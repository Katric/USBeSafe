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
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGE = (SCRIPT_DIR / ".." / ".." / ".." / ".." / "images" / "alpine-base.qcow2").resolve()
QMP_SOCKET = "/tmp/securepass_qmp.sock"

def run_vm_dev():
    if not BASE_IMAGE.exists():
        print("[ERROR] Basisimage nicht gefunden:", BASE_IMAGE)
        sys.exit(1)

    # Check if KVM is available
    kvm_available = os.path.exists("/dev/kvm")

    if os.path.exists(QMP_SOCKET):
        os.remove(QMP_SOCKET)


    qemu_cmd = [
        "qemu-system-x86_64",
        "-m", "2048",
        "-smp", "2",
        "-drive", f"file={BASE_IMAGE},format=qcow2",
        "-net", "nic",
        "-net", "user",
        #"-vnc", ":1",            # VNC auf Port 5901
        #"-display", "sdl",       # GUI Fenstern

        "-nographic",
        "-serial", "mon:stdio",

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

    subprocess.run(qemu_cmd)


if __name__ == "__main__":
    run_vm_dev()
