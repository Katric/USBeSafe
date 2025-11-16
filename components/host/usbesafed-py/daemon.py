import time

import pyudev
from pyudev import Context, Monitor


def handle_add_usb():
    context: Context = pyudev.Context()
    monitor: Monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("=" * 60)
    print("Waiting for new USB Devices... (Event type ADD)")
    print("=" * 60)

    for device in iter(monitor.poll, None):
        device: pyudev.Device = device

        if device is not None and device.action == 'add':
            print('{} connected'.format(device))

            # for key, value in device.items():
            #    print(f"  {key:<20}: {value}")

            # We only listen to the ADD Event of the parent type
            if device.get('DEVTYPE') != 'usb_device':
                print("Device type is {}. Skipping.".format(device.get('DEVTYPE')))
                continue

            # VID, PID and seriel num (for whitelist later)
            vid = device.get('ID_VENDOR_ID')  # VID and PID is mandatory for our tool
            pid = device.get('ID_MODEL_ID')
            # TODO not every device has a unique serial number. Maybe VID/PID is enough for bad usb whitelist?
            serial = device.get('ID_SERIAL_SHORT', None)

            # wait to process all kernel actions
            # TODO try shorter times
            time.sleep(5)

            is_mass_storage = False

            # check if device is mass-storge devicce
            for child in device.children:
                if child.get('DEVTYPE') == 'usb_interface' and child.get('DRIVER') == 'usb-storage':
                    is_mass_storage = True
                    break

            print("\n✅ New USB Device detected!")
            print("-" * 40)
            print(f"  VID               : {vid}")
            print(f"  PID               : {pid}")
            print(f"  Serial Number     : {serial}")
            print(f"  Path              : {device.device_path}")
            print(f"  Is mass storage   : {is_mass_storage}")
            print("-" * 40)

            # TODO: If is mass storage, start VM and attach the device via VID and PID
            # TODO: Add to whitelist if unknown...


def main():
    handle_add_usb()


if __name__ == "__main__":
    main()
