
**NOT YET TESTED**  
_but could be used for inspiration..._

# Securing USB Devices in Linux (BadUSB Protection)

This guide summarizes the steps to safely inspect unknown USB devices on a Linux system, including those that impersonate keyboards (HID devices).

## 1\. Disable Automatic Driver Probing

To prevent Linux from immediately loading the appropriate driver when a USB device is connected (thus activating it), the kernel's `drivers_autoprobe` feature is temporarily disabled.

```bash
echo 0 | sudo tee /sys/bus/usb/drivers_autoprobe
```

  - **Effect**: Connected USB devices will receive power but will not be initialized by the system.
  - **To Re-enable**: `echo 1 | sudo tee /sys/bus/usb/drivers_autoprobe`
  - **Source**: [Official Kernel Documentation (sysfs-bus-usb)](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-bus-usb)

-----

## 2\. Identify and Inspect the Device Type

With automatic probing disabled, the device can be safely identified.

### Check the Device Class with `lsusb`

The `lsusb` utility shows how a device identifies itself to the system.

```bash
# List all devices
lsusb

# Show detailed info for a specific device (e.g., Bus 1, Device 5)
lsusb -v -s 1:5 | grep bInterfaceClass
```

  - **`bInterfaceClass 8 Mass Storage`**: It's a storage device (USB stick).
  - **`bInterfaceClass 3 Human Interface Device`**: It's an input device (keyboard, mouse).
  - **Source**: [USB.org Defined Class Codes](https://www.usb.org/defined-class-codes)

### Display Details with `usb-devices`

This script provides a more readable overview of all USB devices and their properties.

```bash
usb-devices
```

  - **`Cls=08(stor.)`**: Storage device.
  - **`Cls=03(HID )`**: Human Interface Device.
  - **Source**: The command's man page (`man usb-devices`).

-----

## 3\. Safely Mount Storage Devices Manually

If the device is identified as a storage stick, it can be manually mounted with security options to prevent code execution.

```bash
# 1. Create a mount point
sudo mkdir /media/usb

# 2. Mount the stick safely (adjust device name, e.g., /dev/sdb1)
sudo mount -o ro,noexec,nosuid /dev/sdb1 /media/usb
```

  - **`ro`**: Read-only.
  - **`noexec`**: Prevents the execution of binaries.
  - **`nosuid`**: Ignores SUID bits.
  - **Source**: The `mount` command's man page (`man mount`).

-----

## 4\. (Optional) Permanently Blacklist HID Drivers

To prevent generic input devices from ever being loaded automatically, the responsible kernel module can be blacklisted.

```bash
# Create or edit the file
sudo nano /etc/modprobe.d/blacklist-hid.conf

# Add the following line and save:
blacklist hid_generic
```

  - **Effect**: The `hid_generic` driver will no longer be loaded at boot.
  - **Source**: The man page for `modprobe.d` (`man modprobe.d`).
