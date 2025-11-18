# USBeSafe Host Daemon

## Quick Start (Ubuntu/Debian)

### Prerequisites

```sh
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils qemu-kvm wget python3
```

### Run the daemon

```sh
sudo python3 usbesafed.py
```

The daemon will:

1. Check for required system tools
2. Download Alpine virt ISO (first run only)
3. Create base qcow2 image (first run only)
4. Launch interactive installer (first run) – install Alpine into `/dev/vda`
5. Create ephemeral overlay and launch scanning VM
6. Wait for guest daemon to connect over virtio-serial
7. Send `SCAN_USB_DEVICE` command
8. Receive scan result
9. Send `SHUTDOWN` command
10. Clean up overlay and exit

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
