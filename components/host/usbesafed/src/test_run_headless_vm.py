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

QCOW2_BASE_IMAGE_SOURCE = os.path.normpath(os.path.join(SCRIPT_DIR, BASE_IMAGE_REL_TO_SCRIPT))
OVERLAY_IMAGE = QCOW2_BASE_IMAGE_SOURCE.replace("alpine-base.qcow2", "overlay.qcow2")

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
        "-b", QCOW2_BASE_IMAGE_SOURCE,
        OVERLAY_IMAGE
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
        status_window.update("Scan FAILED – malware detected!")
        kill_vm(vm)
        cleanup_overlay()
        return

    if result == "ok":
        status_window.update("Scan clean – waiting for copy…")

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
    context: Context = pyudev.Context()
    monitor: Monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("=" * 60)
    print("Waiting for new USB Devices… (ADD)")
    print("=" * 60)

    for device in iter(monitor.poll, None):

        if device.action != "add":
            continue
        if device.get('DEVTYPE') != 'usb_device':
            continue

        vid = device.get('ID_VENDOR_ID')
        pid = device.get('ID_MODEL_ID')
        serial = device.get('ID_SERIAL_SHORT', None)

        time.sleep(2)

        is_mass_storage = any(
            c.get('DEVTYPE') == "usb_interface" and c.get('DRIVER') == "usb-storage"
            for c in device.children
        )

        if not is_mass_storage:
            continue

        device_info = {"vid": vid, "pid": pid, "serial": serial}

        # ---------------- popup you already implemented ----------------
        if not show_scan_popup(device_info):
            continue

        status = StatusWindow(device_info)
        status.start()
        status.update("Preparing VM…")

        vm_id = os.urandom(4).hex()
        vm_name = f"{VM_NAME_PREFIX}{vm_id}"

        run_prod_scan(vid, pid, vm_name, status)


# ============================================================
#                       MAIN
# ============================================================

def main():
    print("=== USBeSafe Daemon – Production Mode ===")

    handle_add_usb()


if __name__ == "__main__":
    main()
