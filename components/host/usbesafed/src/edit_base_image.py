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

def run_vm_dev():
    if not BASE_IMAGE.exists():
        print("[ERROR] Basisimage nicht gefunden:", BASE_IMAGE)
        sys.exit(1)

    qemu_cmd = [
        "qemu-system-x86_64",
        "-enable-kvm",
        "-m", "2048",
        "-smp", "2",
        "-drive", f"file={BASE_IMAGE},format=qcow2",
        "-net", "nic",
        "-net", "user",
        #"-vnc", ":1",            # VNC auf Port 5901
        #"-display", "sdl",       # GUI Fenstern

        "-nographic",
        "-serial", "mon:stdio",
    ]

    print("[INFO] Starte Entwicklungs-VM…")
    print(" ".join(qemu_cmd))

    subprocess.run(qemu_cmd)

if __name__ == "__main__":
    run_vm_dev()
