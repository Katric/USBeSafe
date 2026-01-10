from select import select

import pyudev
from evdev.ecodes import EV_KEY
from pyudev import Device
from badusb.bad_usb_check import get_ev_key_input_devices

# VID/PID combinations of standard devices on the VM (USB Controllers). Should not be scanned.
SKIP_DEVICES = [("1d6b", "0001"), ("1d6b", "0002"), ("1d6b", "0003")]


def main():
    context = pyudev.Context()

    print(f"Searching for USB Device to be scanned...")

    device_to_scan: list[Device] = []

    vid, pid = None, None

    for device in context.list_devices(subsystem="usb"):
        # using ID_VENDOR_ID and ID_PRODUCT_ID does not work
        vid_bytes = device.attributes.get('idVendor')
        pid_bytes = device.attributes.get('idProduct')

        if vid_bytes is None or pid_bytes is None:
            continue

        # bytes as string
        vid = vid_bytes.decode('utf-8').strip()
        pid = pid_bytes.decode('utf-8').strip()

        if (vid, pid) in SKIP_DEVICES:
            continue

        target_vid = "1532"
        target_pid = "008a"
        if (vid, pid) == (target_vid, target_pid):
            print(f"[INFO]: Found USB Device to scan: {vid} and {pid}")
            device_to_scan.append(device)
            break

    # should never happen because only one device is passed to the VM
    # if len(device_to_scan) != 1:
    #     print(f"Found {len(device_to_scan)} to scan! Must be one device!")
    #     # TODO: write FAIL via virtio
    #     return

    # check for usbhid driver AND hid-generic TODO find difference
    device_to_scan: Device = device_to_scan[0]

    device_drivers = set()
    device_drivers.add(device_to_scan.driver)
    for child in device_to_scan.children:
        device_drivers.add(child.driver)

    if "hid-generic" in device_drivers or "usbhid" in device_drivers:
        devices = get_ev_key_input_devices(vid, pid)

        # device can't send key inputs -> OK!
        if len(devices) == 0:
            print(f"[INFO]: Device {vid} and {pid} can not send key input. No need to scan.")
            return True

        devices = {dev.fd: dev for dev in devices}

        while True:
            r, w, x = select(devices, [], [])
            for fd in r:
                for event in devices[fd].read():
                    if event.type == EV_KEY:
                        print(event)

    # Execute malware scans
    if "usb-storage" in device_drivers:
        # TODO mount and scan
        print("TODO STORAGE")

    # set authorized 0 here


if __name__ == "__main__":
    main()
