#!/usr/bin/env python3

import subprocess
import os
import sys
import time
import socket
import pathlib
import shutil
from pathlib import Path

class VmManager:
    def __init__(self):
        self.vm_process = None
    
    def launch_vm(self, image_path):
        """Launch QEMU VM with the given image"""
        print("[*] Launching headless QEMU/KVM sandbox VM...")
        
        try:
            self.vm_process = subprocess.Popen([
                "qemu-system-x86_64",
                "-m", "512",
                "-smp", "cores=1",
                "-nographic",
                "-nic", "none",
                "-drive", f"file={image_path},format=qcow2,if=virtio",
                "-device", "virtio-serial-pci",
                "-chardev", "socket,path=/tmp/usbesafe.sock,server,nowait,id=ch0",
                "-device", "virtserialport,chardev=ch0,name=com.usbesafe.scan",
                "-cpu", "host,-hypervisor",
                "-machine", "pc,suppress-vmdesc=on",
                "-nodefaults",
                "-qmp", "none",
            ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print(f"[+] VM started (PID: {self.vm_process.pid})")
            time.sleep(2)
            return True
        except Exception as e:
            raise Exception(f"Failed to spawn QEMU: {e}")
    
    def send_to_guest(self, msg):
        """Send message to guest via virtio-serial socket"""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect("/tmp/usbesafe.sock")
            sock.sendall(msg.encode())
            sock.close()
            print(f"[+] Sent to guest: {msg.strip()}")
            return True
        except Exception as e:
            raise Exception(f"Failed to send: {e}")
    
    def recv_from_guest(self):
        """Receive message from guest via virtio-serial socket"""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect("/tmp/usbesafe.sock")
            data = sock.recv(256)
            sock.close()
            return data.decode().strip()
        except Exception as e:
            raise Exception(f"Failed to read: {e}")
    
    def destroy_vm(self):
        """Terminate the VM"""
        if self.vm_process:
            print("[*] Shutting down VM...")
            try:
                os.kill(self.vm_process.pid, 15)  # SIGTERM
                time.sleep(1)
            except:
                pass
            self.vm_process.kill()
            self.vm_process.wait()

def check_system_deps():
    """Check for required system tools"""
    missing = []
    tools = {
        "qemu-system-x86_64": "qemu-system-x86",
        "qemu-img": "qemu-utils",
        "wget": "wget"
    }
    
    for tool, package in tools.items():
        if shutil.which(tool) is None:
            missing.append(package)
    
    if missing:
        print("USBeSafe startup check:\n")
        print(f"Missing system packages detected: {missing}\n")
        print("To install on Debian/Ubuntu, run:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y qemu-system-x86 qemu-utils qemu-kvm wget curl\n")
        print("Then re-run the daemon.\n")
        return False
    
    return True

def find_images_dir():
    """Find or create images directory"""
    images_dir = None
    
    # Try to locate securepass folder from exe path
    try:
        exe_path = Path(sys.executable).resolve()
        p = exe_path.parent
        while p != p.parent:
            if p.name == "securepass":
                images_dir = p / "images"
                break
            p = p.parent
    except:
        pass
    
    # Try from current working directory
    if not images_dir:
        try:
            p = Path.cwd()
            while p != p.parent:
                if p.name == "securepass":
                    images_dir = p / "images"
                    break
                p = p.parent
        except:
            pass
    
    # Default fallback
    if not images_dir:
        images_dir = Path("/opt/usbesafe/images")
    
    # Create if doesn't exist
    try:
        images_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[!] Failed to create images directory {images_dir}: {e}")
        sys.exit(1)
    
    print(f"[*] Using images directory: {images_dir}")
    return images_dir

def create_overlay(backing):
    """Create ephemeral overlay from backing image"""
    import time
    timestamp = int(time.time() * 1000)
    overlay = f"/tmp/usbesafe-overlay-{timestamp}.qcow2"
    
    try:
        subprocess.run([
            "qemu-img", "create", "-f", "qcow2", "-b", str(backing), overlay
        ], check=True, capture_output=True)
        return overlay
    except subprocess.CalledProcessError as e:
        raise Exception(f"qemu-img failed: {e}")

def automated_scan_and_cleanup(vm, overlay_path):
    """Perform scan lifecycle: wait for socket, send SCAN, receive result, shutdown"""
    
    # Wait for socket to appear
    waited = 0
    while not Path("/tmp/usbesafe.sock").exists():
        if waited > 60:
            raise Exception("Timeout waiting for guest socket")
        time.sleep(0.5)
        waited += 1
    
    # Send SCAN command
    vm.send_to_guest("SCAN_USB_DEVICE\n")
    
    # Try to receive response with timeout
    resp = ""
    attempts = 0
    while attempts < 120:
        try:
            s = vm.recv_from_guest()
            if s:
                resp = s
                break
        except:
            pass
        time.sleep(0.25)
        attempts += 1
    
    if not resp:
        print("[!] No response from guest; proceeding to shutdown")
    
    # Ask guest to shutdown
    try:
        vm.send_to_guest("SHUTDOWN\n")
    except:
        pass
    
    # Destroy VM
    vm.destroy_vm()
    
    # Remove overlay
    try:
        os.remove(overlay_path)
        print(f"[+] Removed overlay: {overlay_path}")
    except Exception as e:
        print(f"[!] Failed to remove overlay {overlay_path}: {e}")
    
    return resp

def main():
    print("╔════════════════════════════════════════════╗")
    print("║   USBeSafe Daemon - Secure USB Scanning   ║")
    print("╚════════════════════════════════════════════╝\n")
    
    # Check dependencies
    if not check_system_deps():
        return
    
    # Find images directory
    images_dir = find_images_dir()
    
    prebuilt_scanner = images_dir / "alpine-scanner.qcow2"
    base_image = images_dir / "alpine-base.qcow2"
    iso_path = "/tmp/alpine-virt.iso"
    iso_url = "https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/alpine-virt-3.19.0-x86_64.iso"
    
    # Ensure base image exists
    if not base_image.exists():
        # Download ISO if needed
        if not Path(iso_path).exists():
            print(f"[*] Downloading Alpine ISO to {iso_path}...")
            try:
                subprocess.run(["wget", "-O", iso_path, iso_url], check=True)
                print(f"[+] ISO downloaded: {iso_path}")
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to download ISO: {e}")
                return
        else:
            print(f"[*] ISO already present: {iso_path}")
        
        # Create base qcow2
        print("[*] Creating base qcow2 container (no OS installed)...")
        try:
            subprocess.run([
                "qemu-img", "create", "-f", "qcow2", str(base_image), "2G"
            ], check=True, capture_output=True)
            print(f"[+] Base image created: {base_image}")
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to create image: {e}")
            return
        
        # Boot installer
        print(f"[*] Launching Alpine installer VM so you can install into: {base_image}")
        print("[*] When the installer finishes and you shut down the VM, this daemon will continue and use the installed image.")
        
        try:
            subprocess.run([
                "qemu-system-x86_64",
                "-m", "1024",
                "-smp", "1",
                "-boot", "d",
                "-cdrom", iso_path,
                "-drive", f"file={base_image},format=qcow2,if=virtio",
                "-nographic",
            ])
            print("[+] Installer VM exited (installation likely complete).")
        except Exception as e:
            print(f"[!] Failed to launch installer VM: {e}")
            return
    
    # Check for prebuilt scanner image
    if not prebuilt_scanner.exists():
        scanner_url = os.environ.get("USBESAFE_SCANNER_URL")
        if scanner_url:
            print(f"[*] USBESAFE_SCANNER_URL is set; attempting to download scanner image from: {scanner_url}")
            try:
                subprocess.run(["wget", "-O", str(prebuilt_scanner), scanner_url], check=True)
                print(f"[+] Downloaded prebuilt scanner image to: {prebuilt_scanner}")
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to download scanner image: {e}")
    
    # Select backing image
    if prebuilt_scanner.exists():
        print(f"[*] Using prebuilt scanner image: {prebuilt_scanner}")
        backing = prebuilt_scanner
    else:
        print(f"[*] No prebuilt scanner image found; using base image: {base_image}")
        backing = base_image
    
    # Create overlay
    try:
        overlay_path = create_overlay(backing)
    except Exception as e:
        print(f"[!] Failed to create overlay: {e}")
        return
    
    # Launch VM
    vm = VmManager()
    try:
        vm.launch_vm(overlay_path)
    except Exception as e:
        print(f"[!] {e}")
        os.remove(overlay_path)
        return
    
    print(f"[+] USBeSafe daemon running (ephemeral overlay: {overlay_path})")
    
    # Run automated scan
    try:
        result = automated_scan_and_cleanup(vm, overlay_path)
        print(f"[+] Scan result: {result}")
    except Exception as e:
        print(f"[!] Automated scan failed: {e}")
    
    print("[+] Shutdown complete")

if __name__ == "__main__":
    main()
