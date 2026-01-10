from select import select

import pyudev
from evdev.ecodes import EV_KEY
from pyudev import Device

import host_communication
from badusb.bad_usb_check import get_ev_key_input_devices, wait_for_input, start_red_light_green_light
from host_communication import send_to_host

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

        if (vid, pid) != (None, None):
            print(f"[INFO]: Found USB Device to scan: {vid} and {pid}")
            device_to_scan.append(device)
            break

    # should never happen because only one device is passed to the VM
    if len(device_to_scan) != 1:
        print(f"Found {len(device_to_scan)} to scan! Must be one device!")
        host_communication.send_to_host("fail,")
        return

    # check for usbhid driver AND hid-generic TODO find difference
    device_to_scan: Device = device_to_scan[0]

    device_drivers = set()
    device_drivers.add(device_to_scan.driver)
    for child in device_to_scan.children:
        device_drivers.add(child.driver)

    bad_usb_result = None
    is_usb_storage = False

    if "hid-generic" in device_drivers or "usbhid" in device_drivers:
        bad_usb_result = start_red_light_green_light(vid, pid)
        print(f"[INFO] BadUSB Check OK: ", bad_usb_result)
        if not bad_usb_result:
            send_to_host("fail,")

    # Execute malware scans
    if "usb-storage" in device_drivers:
        is_usb_storage = True
        # TODO mount and scan
        print("TODO STORAGE")

    # if device is HID and not mass storage + bad usb checks successful
    if not is_usb_storage and bad_usb_result:
        host_communication.send_to_host("ok,False")
        return

    if is_usb_storage:
        # todo write return value for shell script
        print("TODO")


if __name__ == "__main__":
    main()
