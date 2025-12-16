#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
import socket
from pathlib import Path
import pyudev
from pyudev import Monitor, Context

from vusb import VirtualUSBStick
from popup import show_delete_vusb_popup, show_scan_popup, StatusWindow
import check_and_load_bad_usb_config

# ---------------- CONFIG ----------------
VM_NAME_PREFIX = "alpine-usb-"

# Base image location (always correct regardless of where script is run)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGE = (SCRIPT_DIR / ".." / ".." / ".." / ".." / "images" / "alpine-base.qcow2").resolve()

# Overlay lives in the same directory as the base image
OVERLAY_IMAGE = BASE_IMAGE.parent / "overlay.qcow2"

QMP_SOCKET = "/tmp/securepass_qmp.sock"
VIRTIO_SOCKET = "/tmp/securepass_virtio.sock"

VUSB_IMMAGE = Path("/tmp/vusb.img")  # temporary vUSB image location


# ============================================================
#                      Dependencies Checker
# ============================================================

def check_system_deps():
    """Check for required system tools"""
    missing = []
    tools = {
        "qemu-system-x86_64": "qemu-system-x86",
        "qemu-img": "qemu-utils",
        "wget": "wget",
        "virsh": "virsh",
        "yad": "yad"
    }

    for tool, package in tools.items():
        if shutil.which(tool) is None:
            missing.append(package)

    if missing:
        print("USBeSafe startup check:\n")
        print(f"Missing system packages detected: {missing}\n")
        print("To install on Debian/Ubuntu, run:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-clients qemu-kvm wget curl yad\n")
        print("Then re-run the daemon.\n")
        return False

    return True


# ============================================================
#                      Disable Auto-Mount
# ============================================================

def disable_udisks2_service():
    """
    Masks and stops udisks2.service to disable auto-mount.
    """

    return  # todo remove return after development is finished to disable udisks2
    # 1. systemctl mask udisks2.service
    mask_command = ["systemctl", "mask", "udisks2.service"]
    try:
        subprocess.run(mask_command, check=True, capture_output=True, text=True)
        print("✅ udisks2 successfully masked.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error when trying to mask udisks2. Code {e.returncode}: {e.stderr.strip()}")
        return False

    # 2. systemctl stop udisks2.service
    stop_command = ["systemctl", "stop", "udisks2.service"]
    try:
        subprocess.run(stop_command, check=True, capture_output=True, text=True)
        print("✅ udisks2 sucessfully stopped.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error when trying to stop udisks2. Code {e.returncode}: {e.stderr.strip()}")
        return False


# ============================================================
#                     OVERLAY CREATION
# ============================================================

def create_overlay():
    print("[INFO] Creating overlay…")

    if os.path.exists(OVERLAY_IMAGE):
        os.remove(OVERLAY_IMAGE)

    subprocess.run([
        "qemu-img", "create",
        "-f", "qcow2",  # <--- format of the new image
        "-F", "qcow2",  # <--- tell QEMU the backing image format
        "-b", str(BASE_IMAGE),
        str(OVERLAY_IMAGE)
    ], check=True)

    print("[INFO] Overlay created:", OVERLAY_IMAGE)


# ============================================================
#                     QEMU START
# ============================================================

def start_vm(vid, pid):
    """
    PRODUCTION VM:
    - headless
    - overlay as root disk
    - virtio-serial port for communication
    - QMP for control
    - pass through the real USB stick
    """

    print("[INFO] Starting scanning VM")
    # Check if KVM is available
    kvm_available = os.path.exists("/dev/kvm")

    # Remove old sockets
    for s in (QMP_SOCKET, VIRTIO_SOCKET):
        if os.path.exists(s):
            os.remove(s)
    try:
        qemu_cmd = [
            "qemu-system-x86_64",
            "-m", "1024",
            "-smp", "2",

            "-drive", f"file={OVERLAY_IMAGE},format=qcow2",

            "-nographic",

            # QEMU won’t bind to your TTY. good for debugging /remove to get access to VM
            # "-serial", "none",

            # --- Virtio communication channel ---
            "-chardev", f"socket,id=virtiocomm,path={VIRTIO_SOCKET},server=on,wait=off",
            "-device", "virtio-serial-pci",
            "-device", "virtserialport,chardev=virtiocomm,name=com.securepass.comm",

            # --- QMP channel ---
            "-qmp", f"unix:{QMP_SOCKET},server,nowait",
            "-usb", # Enable USB
            # --- USB passthrough (real hardware) ---
            "-device", "qemu-xhci,id=xhci",
            "-device", f"driver=usb-host,bus=xhci.0,vendorid=0x{vid},productid=0x{pid}"
        ]

        if kvm_available:
            qemu_cmd.insert(1, "-enable-kvm")
            print("[INFO] KVM acceleration enabled")
        else:
            print("[WARNING] KVM not available, using software emulation (slower)")

        print("[INFO] Launching QEMU:")
        print(" ".join(qemu_cmd))

        vm_process = subprocess.Popen(qemu_cmd)

        print(f"[+] VM started (PID: {vm_process.pid})")

        time.sleep(1)
        return vm_process

    except Exception as e:
        raise Exception(f"Failed to spawn QEMU: {e}")


# ============================================================
#                     VIRTIO MESSAGE RECV
# ============================================================

def wait_for_virtio():
    print("[INFO] Waiting for VM daemon messages…")

    # Wait for virtio socket
    while not os.path.exists(VIRTIO_SOCKET):
        time.sleep(0.2)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(VIRTIO_SOCKET)

        while True:
            data = s.recv(1024).decode().strip()
            if data:
                print(f"[VM → HOST] {data}")
                return data


# ============================================================
#                      QMP CONTROL
# ============================================================

def qmp_send(cmd):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(QMP_SOCKET)
            time.sleep(0.2)
            s.recv(4096)  # QMP greeting
            s.send((cmd + "\n").encode())
            return s.recv(4096).decode()
    except:
        return None


def kill_vm(vm):
    print("[INFO] Stopping VM…")
    try:
        qmp_send('{ "execute": "system_powerdown" }')
        vm.wait(timeout=5)
    except:
        print("[WARN] Hard kill")
        vm.kill()


def cleanup_overlay():
    if os.path.exists(OVERLAY_IMAGE):
        print("[INFO] Removing overlay:", OVERLAY_IMAGE)
        os.remove(OVERLAY_IMAGE)


# ============================================================
#                    EXISTING USB LISTENER
# ============================================================

def handle_add_usb():
    """
    Listens to ADD udev events and reads the following properties:
    - VID
    - PID
    - Serial Number (if present)
    - Path
    - Is mass storage device

    Shows popup, creates status window, then runs the full
    production scanning pipeline (overlay, virtio, QMP, OK/FAIL, copy_done).
    """

    context: Context = pyudev.Context()
    monitor: Monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("=" * 60)
    print("Waiting for new USB Devices... (Event type ADD)")
    print("=" * 60)

    for device in iter(monitor.poll, None):
        device: pyudev.Device = device

        # --- Check correct event type ---
        if device is None or device.action != 'add':
            continue

        ############### SEE DEVICE ATTRIBUTES ###############
        # for key, value in device.items():
        #    print(f"  {key:<20}: {value}")

        print(f"{device} connected")

        # --- Only parent USB device ---
        if device.get('DEVTYPE') != 'usb_device':
            print(f"Device type is {device.get('DEVTYPE')}. Skipping.")
            continue

        # --- VID/PID extraction ---
        vid = device.get('ID_VENDOR_ID')
        pid = device.get('ID_MODEL_ID')
        serial = device.get('ID_SERIAL_SHORT', None)
        #TODO get usb storage size

        # Wait briefly for kernel to finish setting up children
        time.sleep(2)

        # --- Check if USB-storage interface exists ---
        is_mass_storage = False
        for child in device.children:
            if (child.get('DEVTYPE') == 'usb_interface' and
                    child.get('DRIVER') == 'usb-storage'):
                is_mass_storage = True
                break

        print("\n✅ New USB Device detected!")
        print("-" * 40)
        print(f"  VID               : {vid}")
        print(f"  PID               : {pid}")
        print(f"  Serial Number     : {serial}")
        print(f"  Path              : {device.device_path}")
        print(f"  Is mass storage   : {is_mass_storage}")
        print("-" * 40)

        if not is_mass_storage:
            print("Not a mass storage device. Skipping.")
            continue

        # ---------------- popup you already implemented ----------------
        device_info = {"vid": vid, "pid": pid, "serial": serial}

        if not show_scan_popup(device_info):
            print("🚫 Scan cancelled by user")
            continue

        # load usbesafe config file and extract necessary keys
        usbesafe_config = check_and_load_bad_usb_config.load_usbesafe_config()
        is_bad_usb_protection_active: bool = usbesafe_config.get(check_and_load_bad_usb_config.BAD_USB_PROTECTION, 0)

        # ---------------- Status Popup ----------------
        status_window = StatusWindow(device_info)
        status_window.start()
        status_window.update("Building VM configuration...")

        try:
            status_window.update("Preparing VM overlay and starting headless VM...")

            # --- Full Script 3 Logic (overlay + virtio + QMP) ---
            run_prod_scan(vid, pid, status_window)

        except Exception as e:
            status_window.update(f"Error: {str(e)}")
            print(f"[ERROR] Exception during VM scan: {e}")
            time.sleep(3)
            status_window.close()
            raise


# ============================================================
#                       USB LOGIC
# ============================================================

def run_prod_scan(vid, pid, status_window):
    """
    Runs the ENTIRE Script 3 logic:
    - Overlay creation
    - Start VM
    - virtio messaging
    - OK / FAIL handling
    - Wait for copy_done
    - Shutdown
    - Cleanup
    """
    create_overlay()
    vm = start_vm(vid, pid)

    # ---------------- FIRST MESSAGE (OK or FAIL) ----------------
    result = wait_for_virtio()

    if result == "fail":
        status_window.update("Scan FAILED, malware detected!")
        kill_vm(vm)
        cleanup_overlay()
        return

    if result == "ok":
        status_window.update("Scan clean, waiting for copy…")
        # TODO enter real usb size here
        vUSB = VirtualUSBStick(image_path=VUSB_IMMAGE, size_mb=64, qmp_socket=QMP_SOCKET, device_id="vusb1")
        try: 
            vUSB.create(filesystem='vfat', label='USBeSafe')
            vUSB.attach_to_vm()
            status_window.update("vUSB attached to VM, waiting for copy…")
        except Exception as e:
            status_window.update(f"Error setting up vUSB: {e}")
            kill_vm(vm)
            cleanup_overlay()
            return
        # ---------------- WAIT FOR "copy_done" ----------------
        msg = wait_for_virtio()
        if msg == "copy_done":
            status_window.update("Copy completed.")
            time.sleep(2)
            vUSB.detach_from_vm()
            status_window.update("Shutting down VM…")
            kill_vm(vm)
            cleanup_overlay()
            vUSB.mount_on_host()
            status_window.update(f"vUSB mounted on host at {vUSB.host_mount}")
            
            if show_delete_vusb_popup(vUSB.host_mount):
                vUSB.unmount_from_host()
                os.remove(vUSB.image_path)
                status_window.update("Temporary vUSB image deleted.")
            else:
                status_window.update("Temporary vUSB image kept.")

            return

    # unknown
    status_window.update("Unknown VM message.")
    kill_vm(vm)
    cleanup_overlay()


# ============================================================
#                       MAIN
# ============================================================

def main():
    print("=== USBeSafe Daemon, Production Mode ===")

    # Check dependencies
    if not check_system_deps():
        return

    disable_udisks2_service()  # disable and mask udisks2 to disable automount
    handle_add_usb()


if __name__ == "__main__":
    main()
