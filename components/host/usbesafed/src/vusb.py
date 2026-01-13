#!/usr/bin/env python3
"""
Virtual USB Storage Module
Creates and manages virtual USB stick images that can be:
- Attached/detached to QEMU VMs via QMP
- Mounted on the host system
"""

import os
import subprocess
import json
import socket
import time
from pathlib import Path
import getpass


class VirtualUSBStick:
    """Manages a virtual USB stick image file"""
    
    def __init__(self, image_path, size_mb=100,qmp_socket="/tmp/qmp.sock", device_id='vusb0'):
        """
        Initialize virtual USB stick
        
        Args:
            image_path: Path to the image file
            size_mb: Size in MB (default 100MB)
        """
        self.device_id = device_id
        self.image_path = Path(image_path)
        self.size_mb = size_mb
        self.loop_device = None
        self.qmp_client = QMPClient(qmp_socket)
        self.host_mount = f"/media/{getpass.getuser()}/USBeSafe"
        
    def create(self, filesystem='vfat', label='VUSB'):
        """
        Create a new virtual USB stick image
        
        Args:
            filesystem: Filesystem type (vfat, ext4, etc.)
            label: Volume label
        """
        print(f"[+] Creating virtual USB stick: {self.image_path}")
        
        # Create image file
        try:
            subprocess.run([
                'dd', 
                'if=/dev/zero', 
                f'of={self.image_path}',
                'bs=1M',
                f'count={self.size_mb}'
            ], check=True, capture_output=True)
            print(f"[+] Image file created ({self.size_mb}MB)")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create image: {e.stderr.decode()}")
        
        # Format with filesystem
        try:
            if filesystem == 'vfat':
                subprocess.run([
                    'mkfs.vfat',
                    '-n', label,
                    str(self.image_path)
                ], check=True, capture_output=True)
            elif filesystem == 'ext4':
                subprocess.run([
                    'mkfs.ext4',
                    '-L', label,
                    str(self.image_path)
                ], check=True, capture_output=True)
            else:
                raise ValueError(f"Unsupported filesystem: {filesystem}")
                
            print(f"[+] Formatted with {filesystem} filesystem (label: {label})")
            return True
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to format image: {e.stderr.decode()}")
    
    def exists(self):
        """Check if image file exists"""
        return self.image_path.exists()
    
    def mount_on_host(self):
        """
        Mount the virtual USB stick on the host system
        
        Args:
            mount_point: Directory where to mount
        """
        mount_point = Path(self.host_mount)
        
        if not mount_point.exists():
            mount_point.mkdir(parents=True, exist_ok=True)
        
        print(f"[+] Mounting {self.image_path} to {mount_point}")
        
        try:
            # Setup loop device
            result = subprocess.run([
                'losetup',
                '--find',
                '--show',
                str(self.image_path)
            ], check=True, capture_output=True, text=True)
            
            self.loop_device = result.stdout.strip()
            print(f"[+] Loop device: {self.loop_device}")
            
            # Mount
            subprocess.run([
                'mount',
                self.loop_device,
                str(mount_point)
            ], check=True, capture_output=True)
            
            print(f"[+] Mounted successfully at {mount_point}")
            return True
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to mount: {e.stderr.decode()}")
    
    def unmount_from_host(self):
        """
        Unmount the virtual USB stick from the host

        Args:
            mount_point: Directory where it's mounted
        """
        mount_point = Path(self.host_mount)
        print(f"[+] Unmounting {mount_point}")

        try:
            # Flush pending writes
            subprocess.run(["sync"], check=False)

            # Unmount (retry a bit if busy)
            last_err = ""
            for _ in range(5):
                p = subprocess.run(
                    ["umount", str(mount_point)],
                    capture_output=True,
                    text=True
                )
                if p.returncode == 0:
                    print(f"[+] Unmounted from {mount_point}")
                    break

                last_err = (p.stderr or "").strip()

                # Already unmounted -> treat as success
                if "not mounted" in last_err.lower():
                    break

                # Busy -> wait and retry
                if "busy" in last_err.lower():
                    time.sleep(0.5)
                    continue

                # Other error -> stop immediately
                raise Exception(f"Failed to unmount: {last_err}")
            else:
                # Still busy after retries -> lazy unmount
                subprocess.run(
                    ["umount", "-l", str(mount_point)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"[+] Lazy-unmounted {mount_point}")

            # Detach loop device (use stored loop device if known)
            if self.loop_device:
                subprocess.run(
                    ["losetup", "-d", self.loop_device],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"[+] Loop device {self.loop_device} detached")
                self.loop_device = None
            else:
                # Fallback: detach any loop device currently backed by this image
                p = subprocess.run(
                    ["losetup", "-j", str(self.image_path)],
                    capture_output=True,
                    text=True
                )
                if p.returncode == 0 and p.stdout.strip():
                    # Example line: /dev/loop7: [xxxx]: (/tmp/vusb.img)
                    loopdev = p.stdout.split(":", 1)[0].strip()
                    subprocess.run(
                        ["losetup", "-d", loopdev],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print(f"[+] Loop device {loopdev} detached (fallback)")

            return True

        except subprocess.CalledProcessError as e:
            # text=False here, so stderr is bytes -> decode safely
            stderr = e.stderr.decode(errors="replace") if e.stderr else str(e)
            raise Exception(f"Failed to unmount: {stderr}")
        
    def attach_to_vm(self):
        """
        Attach the virtual USB stick to a QEMU VM via QMP
        
        Args:
            device_id: Device ID for the USB storage
        """
        try:
            self.qmp_client.connect()
            time.sleep(1)
            result = self.qmp_client.attach_usb_storage(
                str(self.image_path), device_id=self.device_id
            )
            time.sleep(1)
            self.qmp_client.disconnect()
            return result
        except Exception as e:
            print(f"Failed to attach to VM: {e}")
    
    def detach_from_vm(self):
        """
        Detach the virtual USB stick from the QEMU VM via QMP
        
        Args:
            device_id: Device ID of the USB storage
        """
        try:
            self.qmp_client.connect()
            time.sleep(1) 
            result = self.qmp_client.detach_usb_storage(device_id=self.device_id)
            time.sleep(1)
            self.qmp_client.disconnect()
            return result
        except Exception as e:
            print(f"Failed to detach from VM: {e}")


class QMPClient:
    """Simple QMP (QEMU Machine Protocol) client"""
    
    def __init__(self, socket_path):
        """
        Initialize QMP client
        
        Args:
            socket_path: Path to QEMU QMP socket
        """
        self.socket_path = socket_path
        self.sock = None
    
    def connect(self):
        """Connect to QMP socket"""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        
        # Read QMP greeting
        greeting = self._recv()
        print(f"[+] QMP greeting: {greeting.get('QMP', {}).get('version', {})}")
        
        # Send qmp_capabilities
        self._send({'execute': 'qmp_capabilities'})
        response = self._recv()
        
        if 'error' in response:
            raise Exception(f"QMP capabilities negotiation failed: {response['error']}")
        
        print("[+] QMP connection established")
        return True
    
    def disconnect(self):
        """Disconnect from QMP socket"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def _send(self, command):
        """Send QMP command"""
        data = json.dumps(command) + '\n'
        self.sock.sendall(data.encode())
    
    def _recv(self):
        """Receive QMP response"""
        data = b''
        while True:
            chunk = self.sock.recv(4096)
            data += chunk
            if b'\n' in chunk:
                break
        
        # Handle multiple JSON objects (events + response)
        lines = data.decode().strip().split('\n')
        for line in lines:
            if line:
                obj = json.loads(line)
                if 'return' in obj or 'error' in obj or 'QMP' in obj:
                    return obj
        
        return json.loads(lines[-1]) if lines else {}
    
    def execute(self, command, **arguments):
        """
        Execute QMP command
        
        Args:
            command: QMP command name
            **arguments: Command arguments
        """
        cmd = {'execute': command}
        if arguments:
            cmd['arguments'] = arguments
        
        self._send(cmd)
        response = self._recv()
        
        if 'error' in response:
            raise Exception(f"QMP command failed: {response['error']}")
        
        return response.get('return')
    
    def attach_usb_storage(self, image_path, device_id='vusb0'):
        """
        Attach virtual USB storage to VM
        
        Args:
            image_path: Path to the image file
            device_id: Device ID for the USB storage
        """
        print(f"[+] Attaching USB storage to VM: {image_path}")
        
        # Add drive using drive_add (older QMP style that works more reliably)
        drive_id = f'drive-{device_id}'
        self.execute(
            'blockdev-add',
            driver='file',
            **{
                'node-name': drive_id,
                'filename': str(image_path)
            }
        )
        print(f"[+] Block device added: {drive_id}")
        
        # Add USB storage device
        self.execute(
            'device_add',
            driver='usb-storage',
            id=device_id,
            drive=drive_id
        )
        print(f"[+] USB storage device added: {device_id}")
        
        return device_id
    
    def detach_usb_storage(self, device_id='vusb0'):
        """
        Detach virtual USB storage from VM
        
        Args:
            device_id: Device ID of the USB storage
        """
        print(f"[+] Detaching USB storage from VM: {device_id}")
        
        # Remove USB device
        self.execute('device_del', id=device_id)
        print(f"[+] USB device removed: {device_id}")
        
        # Wait a bit for device removal
        time.sleep(1)
        
        # Remove block device
        drive_id = f'drive-{device_id}'
        self.execute('blockdev-del', **{'node-name': drive_id})
        print(f"[+] Block device removed: {drive_id}")
        
        return True
