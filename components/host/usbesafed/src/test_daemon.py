"""
edit_base_image.py
------------------
Starts the base VM image with GUI and enabled networking in development mode.
Used to install packages, configure the scanner, modify the daemon, and make
any changes to the base image. No overlays, no headless mode.
"""

#!/usr/bin/env python3
import subprocess
import os
import sys
import time
import socket
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGE = (SCRIPT_DIR / ".." / ".." / ".." / ".." / "images" / "alpine-base.qcow2").resolve()
QMP_SOCKET = "/tmp/securepass_qmp.sock"
VIRTIO_SOCKET = "/tmp/securepass_virtio.sock"


def _virtio_test_host_side(timeout_sec: float = 200.0) -> bool:
    """
    Minimal test:
    - waits for the virtio unix socket to appear
    - connects (HOST -> QEMU)
    - sends 'ping'
    - tries to read a reply (VM -> HOST) (optional, depends on guest daemon)
    """
    print("[INFO] Virtio test: waiting for virtio socket:", VIRTIO_SOCKET)

    start = time.time()
    while not os.path.exists(VIRTIO_SOCKET):
        if time.time() - start > timeout_sec:
            print("[WARN] Virtio test: socket did not appear within timeout.")
            return False
        time.sleep(0.1)

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            s.connect(VIRTIO_SOCKET)

            msg = "ping\n".encode()
            s.sendall(msg)
            print("[HOST → VM] ping")

            try:
                data = s.recv(1024)
                if data:
                    print("[VM → HOST]", data.decode(errors="replace").strip())
                    return True
                print("[WARN] Virtio test: no reply received (guest may not be responding).")
                return True
            except socket.timeout:
                print("[WARN] Virtio test: recv timeout (guest may not be responding).")
                return True

    except Exception as e:
        print(f"[ERROR] Virtio test failed: {e}")
        return False


def run_vm_dev():
    if not BASE_IMAGE.exists():
        print("[ERROR] Basisimage nicht gefunden:", BASE_IMAGE)
        sys.exit(1)

    # Check if KVM is available
    kvm_available = os.path.exists("/dev/kvm")

    # Remove old sockets
    for s in (QMP_SOCKET, VIRTIO_SOCKET):
        if os.path.exists(s):
            os.remove(s)

    qemu_cmd = [
        "qemu-system-x86_64",
        "-m", "2048",
        "-smp", "2",
        "-drive", f"file={BASE_IMAGE},format=qcow2",
        "-net", "nic",
        "-net", "user",
        #"-vnc", ":1",            # VNC auf Port 5901
        "-display", "sdl",       # GUI Fenstern

        #"-nographic",
        "-serial", "mon:stdio",

        # --- Virtio communication channel (from Script 2) ---
        "-chardev", f"socket,id=virtiocomm,path={VIRTIO_SOCKET},server=on,wait=off",
        "-device", "virtio-serial-pci",
        "-device", "virtserialport,chardev=virtiocomm,name=com.securepass.comm",

        "-usb",                  # Enable USB
        "-device", "usb-ehci,id=ehci",  # USB 2.0 controller
        # --- QMP channel ---
        "-qmp", f"unix:{QMP_SOCKET},server,nowait",
    ]

    if kvm_available:
        qemu_cmd.insert(1, "-enable-kvm")
        print("[INFO] KVM acceleration enabled")
    else:
        print("[WARNING] KVM not available, using software emulation (slower)")

    print("[INFO] Starte Entwicklungs-VM…")
    print(" ".join(qemu_cmd))

    # Start QEMU without blocking so we can test the virtio socket
    vm_process = subprocess.Popen(qemu_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Test host-side socket connectivity (VM reply depends on guest-side daemon)
    _virtio_test_host_side()

    # Keep same behavior as subprocess.run(): block until VM exits
    vm_process.wait()


if __name__ == "__main__":
    run_vm_dev()


# to test the vm to host connection run the script and run in the vm terminal:
# echo "hello-from-vm" > /dev/virtio-ports/com.securepass.comm
