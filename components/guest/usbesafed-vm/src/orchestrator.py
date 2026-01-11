import os
import subprocess
import time

import pyudev
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

    if "hid-generic" in device_drivers or "usbhid" in device_drivers:
        bad_usb_result = start_red_light_green_light(vid, pid)
        print(f"[INFO] BadUSB Check OK: ", bad_usb_result)
        if not bad_usb_result:
            send_to_host("fail,")
            return

    # Trigger the execution of malware scans by mounting on /mnt/realusb.
    # TODO what to do if usb has multiple partitions?!
    if "usb-storage" in device_drivers:
        # create mount point
        mount_point = "/mnt/realusb"
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)

        potential_devices = ["/dev/sdb1", "/dev/sdb"]
        mounted_successfully = False
        detected_fstype = None

        for device_path in potential_devices:
            if not os.path.exists(device_path):
                continue

            print(f"[INFO] Analyzing {device_path}...")
            # find file system type
            try:
                blkid_out = subprocess.check_output(
                    ["blkid", "-o", "value", "-s", "TYPE", device_path],
                    stderr=subprocess.DEVNULL
                )
                detected_fstype = blkid_out.decode('utf-8').strip()
            except subprocess.CalledProcessError:
                print(f"[DEBUG] No file system found for {device_path}.")
                continue

            if not detected_fstype:
                continue

            print(f"[INFO] Found file system for {device_path}: {detected_fstype}")

            mount_opts = ["-o", "ro,noexec"]

            mount_cmd = ["mount", "-t", detected_fstype] + mount_opts + [device_path, mount_point]

            try:
                print(f"[INFO] Trying to mount on: {' '.join(mount_cmd)}")
                subprocess.run(mount_cmd, check=True)
                print(f"[SUCCESS] Successfully mounted on {mount_point} (Type: {detected_fstype})")
                mounted_successfully = True
                return
            except subprocess.CalledProcessError as e:
                print(f"[WARN] Mount failed for {device_path}: {e}")
                continue

        if not mounted_successfully:
            print("[ERROR] Could not mount or no filesystem detected.")
            host_communication.send_to_host("fail,")
            return

    # if device is HID and not mass storage
    host_communication.send_to_host("ok,False")
    return


if __name__ == "__main__":
    main()
