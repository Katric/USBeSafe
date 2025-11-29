"""
create_base_image.py
--------------------
This script checks whether the base VM image already exists. If not, it automatically
downloads the Alpine image, creates the base-vm.qcow2 file, and stores it under
securepass/images. Used only for initial setup or re-creation of the base image.
"""


#!/usr/bin/env python3
import subprocess
import os
import sys
from pathlib import Path
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR / ".." / ".." / ".." / ".." / "images"
BASE_DIR = BASE_DIR.resolve()

BASE_IMAGE = BASE_DIR / "alpine-base.qcow2"
ISO_PATH   = BASE_DIR / "alpine.iso"

# Beispiel-URL – kannst du anpassen
ALPINE_ISO_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/alpine-standard-3.22.2-x86_64.iso"

def download_iso():
    print("[INFO] Lade Alpine ISO herunter…")
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(ALPINE_ISO_URL, ISO_PATH)
    print("[INFO] ISO gespeichert unter:", ISO_PATH)

def create_qcow():
    print("[INFO] Erstelle neues qcow2 Image…")
    subprocess.run([
        "qemu-img", "create",
        "-f", "qcow2",
        str(BASE_IMAGE),
        "4G"
    ], check=True)
    print("[INFO] qcow2 erstellt:", BASE_IMAGE)

def start_installation_vm():
    print("[INFO] Starte VM zur Installation…")
    cmd = [
        "qemu-system-x86_64",
        "-enable-kvm",
        "-m", "2048",
        "-smp", "2",
        "-drive", f"file={BASE_IMAGE},format=qcow2",
        "-cdrom", str(ISO_PATH),
        "-boot", "d",
        "-net", "nic",
        "-net", "user",
        "-vnc", ":2",
        "-display", "sdl",
    ]
    print("[INFO] VM mit Installations-ISO gestartet.")
    subprocess.run(cmd)

def main():
    if BASE_IMAGE.exists():
        print("[INFO] Basisimage existiert bereits:", BASE_IMAGE)
        return

    print("[INFO] Basisimage nicht gefunden – erstelle neues.")

    if not ISO_PATH.exists():
        download_iso()

    create_qcow()
    start_installation_vm()

    print("\n[INFO] Setup abgeschlossen.")
    print("[INFO] Nach der Installation bitte VM herunterfahren.")
    print("[INFO] Danach ist das Basisimage bereit.")

if __name__ == "__main__":
    main()
