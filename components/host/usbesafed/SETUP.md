# USBeSafe VM Host Components

## File Overview

- `create_base_image.py`  
  One-time setup. Downloads Alpine Linux, creates `alpine-base.qcow2` under `securepass/images/` and starts the interactive installer inside QEMU.

- `edit_base_image.py`  
  Development mode for the base image. Boots `alpine-base.qcow2` with GUI + networking so you can install packages, configure the scanner, and drop in `vm-daemon.sh`.

- `vm_run.py`  
  Production runner. Boots the VM **headless** from an overlay based on `alpine-base.qcow2`, sets up virtio/QMP and orchestrates the scan workflow.

- `securepass/images/`  
  - `alpine-base.qcow2` – installed Alpine base VM (created once by `create_base_image.py`).  
  - `alpine.iso` – Alpine installer ISO (downloaded by `create_base_image.py`).

---

## Host Requirements (Ubuntu/Debian)

```sh
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils qemu-kvm wget python3
```

---

## Typical Workflow

1. **Initial setup (once per machine)**  
   Run `create_base_image.py` to download Alpine and install it into `alpine-base.qcow2`.

2. **Configure base image (whenever you need to modify the VM)**  
   Run `edit_base_image.py` to boot the VM with GUI + network and:
   - install packages (scanner, tools, shell, etc.)
   - drop in and enable `vm-daemon.sh`
   - tweak config

3. **Use for scanning (normal operation)**  
   Run `vm_run.py` from the host:
   - creates overlay on top of `alpine-base.qcow2`
   - boots VM headless with virtio/QMP
   - waits for guest daemon messages
   - coordinates scan / copy / teardown

---

## 1️⃣ `create_base_image.py` – One-time Alpine Installation

Run:

```sh
python3 create_base_image.py
```

Installer steps (compact):

1. Login: `root`
2. Run: `setup-alpine`
3. Keymap: `ge` → variant: `ge-nodeadkeys`
4. Hostname: Enter
5. Network: Enter for `eth0`, DHCP, no manual config
6. Root password: choose simple one (root)
7. Timezone: `Europe/Berlin`
8. Proxy: Enter
9. APK mirror: Enter
10. User: `no` (root only)
11. SSH server: `none`
12. Root SSH login: `no`
13. SSH key: Enter
14. Disk: `sda`
15. Mode: `sys`
16. Confirm wipe
17. Shutdown: `poweroff`

---

## 2️⃣ `edit_base_image.py` – Edit Base VM

```sh
python3 edit_base_image.py
```

Use this VM session to:

- install packages
- add `vm-daemon.sh`
- add `init-script.sh`
- install Scanner

Shutdown with:

```sh
poweroff
```

---

## 3️⃣ `vm_run.py` – Headless Production Run

```sh
python3 vm_run.py
```

Behavior:

- creates overlay
- boots VM headless with virtio-serial
- waits for daemon messages
- handles ok/fail/copy-done
- destroys overlay afterward



## Manual Communication Testing

Test the socket manually with netcat or Python:

```sh
# Terminal 1: Start the daemon
sudo python3 usbesafed.py

# Terminal 2: Send a command
echo -n "SCAN_USB_DEVICE" | nc -U /tmp/usbesafe.sock

# Listen for responses
nc -U /tmp/usbesafe.sock
```

Or with Python:

```python
import socket

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/tmp/usbesafe.sock")
sock.sendall(b"SCAN_USB_DEVICE\n")
print(sock.recv(256).decode())
sock.close()
```

Start program with sudo: (from )
First download Alpine x86_64 image and put it in THIS directory (TODO: move to images dir)
https://alpinelinux.org/downloads/

```bash
sudo .venv/bin/python components/host/usbesafed/src/usbesafed.py 
```

## The configuration file against BadUSB Protection

The daemon reads a configuration file containing the 'BAD_USB_PROTECTION' flag. This value (0 or 1) decides if the
BadUSB Protection should be used or not.  
You can create the file and its contents directly by running the following command:
