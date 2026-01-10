import pyudev
from pyudev import Device

# VID/PID combinations of standard devices on the VM (USB Controllers). Should not be scanned.
SKIP_DEVICES = [("1d6b", "0001"), ("1d6b", "0002"), ("1d6b", "0003")]


def main():
    context = pyudev.Context()

    print(f"Searching for USB Device to be scanned...")

    device_to_scan: list[Device] = []

    for device in context.list_devices(subsystem="usb"):
        # print(device.driver) THIS PRINTS THE DEVICES DRIVERS!!!!
        vid = device.get('ID_VENDOR_ID', device.get('ID_VENDOR', None))
        pid = device.get('ID_MODEL_ID', None)

        if (vid, pid) in SKIP_DEVICES:
            print(f"Skipping device {vid} and {pid}")
            continue

        if (vid, pid) != (None, None):
            print(f"Found USB Device {vid} and {pid}")
            device_to_scan.append(device)

    # should never happen because only one device is passed to the VM
    if len(device_to_scan) != 1:
        print(f"Found {len(device_to_scan)} to scan! Must be one device!")
        # TODO: write FAIL via virtio
        return

    # check for usbhid driver AND hid-generic TODO find difference
    device_to_scan: Device = device_to_scan[0]

    device_drivers = set()
    device_drivers.add(device_to_scan.driver)
    for child in device_to_scan.children:
        device_drivers.add(child.driver)

    device_to_scan.device_path

    if "hid-generic" in device_drivers or "usbhid" in device_drivers:
        # check keymap -> is this a keyboard? or has EV_KEY events?
        # ask user: PLugged in a keyboard or a device with buttons?
        # perform BadUSB scans
        print("TODO")

    # Execute malware scans
    if "usb-storage" in device_drivers:
        print("TODO")

    # set authorized 0 here


if __name__ == "__main__":
    main()
