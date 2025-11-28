#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
import socket
from pathlib import Path
import pyudev

from popup import show_scan_popup, StatusWindow


SCRIPT_FILE_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_FILE_PATH)
BASE_IMAGE_REL_TO_SCRIPT = os.path.join('..', '..', '..', '..', 'images', 'alpine-base.qcow2')

# ---------------- CONFIG ----------------
VM_NAME_PREFIX = "alpine-usb-"

# Base image location (always correct regardless of where script is run)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGE = (SCRIPT_DIR / ".." / ".." / ".." / ".." / "images" / "alpine-base.qcow2").resolve()

# Overlay lives in the same directory as the base image
OVERLAY_IMAGE = BASE_IMAGE.parent / "overlay.qcow2"

QMP_SOCKET = "/tmp/securepass_qmp.sock"
VIRTIO_SOCKET = "/tmp/securepass_virtio.sock"


# ============================================================
#                     OVERLAY CREATION
# ============================================================

def create_overlay():
    print("[INFO] Creating overlay…")

    if os.path.exists(OVERLAY_IMAGE):
        os.remove(OVERLAY_IMAGE)

    subprocess.run([
        "qemu-img", "create",
        "-f", "qcow2",
        "-F", "qcow2",              # <--- tell QEMU the base format
        "-b", str(BASE_IMAGE),
        str(OVERLAY_IMAGE)
    ], check=True)


    print("[INFO] Overlay created:", OVERLAY_IMAGE)


# ============================================================
#                     QEMU START
# ============================================================

def start_vm(vid, pid, drive_name):
    """
    PRODUCTION VM:
    - headless
    - overlay as root disk
    - virtio-serial port for communication
    - QMP for control
    - pass through the real USB stick
    """

    print(f"[INFO] Starting scanning VM for drive '{drive_name}'")

    # Remove old sockets
    for s in (QMP_SOCKET, VIRTIO_SOCKET):
        if os.path.exists(s):
            os.remove(s)

    qemu_cmd = [
        "qemu-system-x86_64",
        "-enable-kvm",
        "-m", "1024",
        "-smp", "2",

        "-drive", f"file={OVERLAY_IMAGE},format=qcow2",

        "-nographic",

        # --- Virtio communication channel ---
        "-chardev", f"socket,id=virtiocomm,path={VIRTIO_SOCKET},server,nowait",
        "-device", "virtio-serial-pci",
        "-device", "virtserialport,chardev=virtiocomm,name=com.securepass.comm",

        # --- QMP channel ---
        "-qmp", f"unix:{QMP_SOCKET},server,nowait",

        # --- USB passthrough (real hardware) ---
        "-device", "qemu-xhci,id=xhci",
        f"-device=usb-host,bus=xhci.0,vendorid=0x{vid},productid=0x{pid}",
    ]

    print("[INFO] Launching QEMU:")
    print(" ".join(qemu_cmd))

    vm_process = subprocess.Popen(qemu_cmd)
    time.sleep(1)
    return vm_process


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
#                       USB LOGIC
# ============================================================

def run_prod_scan(vid, pid, vm_name, status_window):
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
    vm = start_vm(vid, pid, vm_name)

    # ---------------- FIRST MESSAGE (OK or FAIL) ----------------
    result = wait_for_virtio()

    if result == "fail":
        status_window.update("Scan FAILED, malware detected!")
        kill_vm(vm)
        cleanup_overlay()
        return

    if result == "ok":
        status_window.update("Scan clean, waiting for copy…")

        # ---------------- WAIT FOR "copy_done" ----------------
        msg = wait_for_virtio()
        if msg == "copy_done":
            status_window.update("Copy completed.")
            kill_vm(vm)
            cleanup_overlay()
            return

    # unknown
    status_window.update("Unknown VM message.")
    kill_vm(vm)
    cleanup_overlay()


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

    Starts VM and attaches a connected USB device (if it is mass storage) to the started VM
    """
    context: Context = pyudev.Context()
    monitor: Monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("=" * 60)
    print("Waiting for new USB Devices... (Event type ADD)")
    print("=" * 60)

    for device in iter(monitor.poll, None):
        device: pyudev.Device = device

        if device is not None and device.action == 'add':
            print('{} connected'.format(device))

            # for key, value in device.items():
            #    print(f"  {key:<20}: {value}")

            # We only listen to the ADD Event of the parent type
            if device.get('DEVTYPE') != 'usb_device':
                print("Device type is {}. Skipping.".format(device.get('DEVTYPE')))
                continue

            # VID, PID and seriel num (for whitelist later)
            vid = device.get('ID_VENDOR_ID')  # VID and PID is mandatory for our tool
            pid = device.get('ID_MODEL_ID')
            # TODO not every device has a unique serial number. Maybe VID/PID is enough for bad usb whitelist?
            serial = device.get('ID_SERIAL_SHORT', None)

            # wait to process all kernel actions
            # TODO try shorter time
            time.sleep(2)

            is_mass_storage = False

            # check if device is mass-storge devicce
            for child in device.children:
                if child.get('DEVTYPE') == 'usb_interface' and child.get('DRIVER') == 'usb-storage':
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

            if is_mass_storage:
                # Show popup and ask user if device should be scanned
                device_info = {
                    'vid': vid,
                    'pid': pid,
                    'serial': serial
                }

                if not show_scan_popup(device_info):
                    print("🚫 Scan cancelled by user")
                    continue

                # Create status window to show scan progress
                status_window = StatusWindow(device_info)
                status_window.start()

                try:
                    vm_id = os.urandom(4).hex()
                    vm_name = f"{VM_NAME_PREFIX}{vm_id}"

                    status_window.update("Building VM configuration...")

                    is_vm_started = start_vm(vid, pid, vm_name)

                    status_window.update("Starting VM and attaching USB device...")
                    if is_vm_started:
                        status_window.update("VM started successfully - Scanning USB device...")
                        print("VM started and USB passed")
                        # Keep status window open while VM is running
                        time.sleep(5)  # Show success message briefly
                        status_window.update("Scan in progress - VM is running...")
                        # TODO: Monitor VM status and update accordingly
                        # TODO temporary QCOW file has to be deleted manually after shutdown under vm_disk_path
                    else:
                        status_window.update("Error: Failed to start VM")
                        time.sleep(3)
                        status_window.close()
                except Exception as e:
                    status_window.update(f"Error: {str(e)}")
                    time.sleep(3)
                    status_window.close()
                    raise


# ============================================================
#                       MAIN
# ============================================================

def main():
    print("=== USBeSafe Daemon – Production Mode ===")

    # Check dependencies
    if not check_system_deps():
        return


    disable_udisks2_service()  # disable and mask udisks2 to disable automount
    handle_add_usb()


if __name__ == "__main__":
    main()
