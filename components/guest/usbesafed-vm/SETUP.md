# USBeSafe VM Daemon — Implementation Guide (Alpine Linux)

This document describes **how to deploy and enable the USBeSafe VM daemon** inside the Alpine-based guest VM.

It intentionally focuses on **commands and steps**, **not on code**, so it can be used as an installation / handover document.

---

## Scope & Responsibility

This guide covers **only the VM-side setup**:

- installing the daemon script
- registering it with OpenRC
- enabling and starting the service
- verifying virtio communication

---

## Preconditions

Inside the VM, the following must already exist:

- Alpine Linux with OpenRC
- BusyBox core utilities (`sh`, `df`, `cp`, `awk`)
- A virtio-serial device exposed by QEMU:
  - `/dev/virtio-ports/com.securepass.comm`
- A scanner implementation already present:
  - e.g. `scanner.py` (exact logic irrelevant here)

---

## Step 1: Install the VM Daemon Script

1. Copy the daemon shell script (usbesafed-vm.sh) to:
   ```
   /usr/local/bin/usbesafed-vm.sh
   ```

2. Make the script executable:
   ```
   chmod +x /usr/local/bin/usbesafed-vm.sh
   ```

The daemon is **self-contained** and does not require any external config files.

---

## Step 2: Install the OpenRC Init Script

1. Copy the OpenRC init script (usbesafed-vm) to:
   ```
   /etc/init.d/usbesafed-vm
   ```

2. Make it executable:
   ```
   chmod +x /etc/init.d/usbesafed-vm
   ```

---

## Step 3: Enable the Daemon at Boot

Register the daemon so it starts automatically:

```
rc-update add usbesafed-vm default
```

This ensures the daemon starts on every VM boot.

---

## Step 4: Start the Daemon Manually (for Testing)

Start the service immediately:

```
rc-service usbesafed-vm start
```

Check its status:

```
rc-service usbesafed-vm status
```

---

## Step 5: Runtime Expectations

Once running, the daemon behaves as follows:

1. Waits until the **real USB stick** appears inside the VM  
   (at a predefined mount point).

2. Automatically runs the **scanner** on the USB contents.

3. If the scan fails:
   - sends `fail` via virtio
   - performs no further actions

4. If the scan succeeds:
   - calculates the **used size of the USB**
   - rounds the value **up to full GiB**
   - sends:
     - `size_gb:<N>`
     - `ok`
     over the virtio channel

   *(Purpose: the host uses this information to create a correctly sized virtual USB stick.)*

5. Waits for the **virtual USB stick** to appear (host attaches it via QMP).

6. Copies all data from real USB → virtual USB.

7. Sends `copy_done` via virtio.

8. Waits until both USBs are removed before restarting the cycle.

---

## Step 6: Verifying Virtio Communication

To verify that VM → Host communication works:

- Ensure the virtio port exists:
  ```
  ls -l /dev/virtio-ports/
  ```

- The entry `com.securepass.comm` **must exist** and point to a `vport*` device.

- When the daemon runs and events occur, the host should receive:
  - `fail`
  - or `size_gb:N`
  - followed by `ok`
  - followed by `copy_done`

---

## Notes & Design Guarantees

- The VM daemon:
  - does **not** manage VM lifecycle
  - does **not** attach USB devices
  - does **not** delete overlays
  - does **not** shut down the VM

- The VM only **signals state**.
- The host is the **single authority** for:
  - QMP actions
  - overlay cleanup
  - user notifications
  - VM shutdown

---

## Troubleshooting Checklist

- Daemon not starting:
  - check executable bits on both files
  - verify OpenRC is running

- No virtio messages:
  - confirm `/dev/virtio-ports/com.securepass.comm` exists
  - verify QEMU was started with `virtio-serial` + `virtserialport`

- Copy never starts:
  - ensure the virtual USB is actually mounted inside the VM
  - mounting is outside the daemon’s responsibility

---

## End of Document