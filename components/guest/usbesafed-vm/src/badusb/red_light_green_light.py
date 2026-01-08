from select import select

import evdev
from evdev import ecodes, InputDevice
from evdev.ecodes import EV_KEY, EV_REL


# Execute with sudo! otherwise can't list devices
def main():
    vid = "1532"
    pid = "008a"

    devices = get_ev_key_input_devices(vid, pid)

    # device can't send key inputs -> OK!
    if len(devices) == 0:
        return True

    devices = {dev.fd: dev for dev in devices}

    iterations = 0
    while True:
        iterations += 1
        print("Iteration " + str(iterations))
        r, w, x = select(devices, [], [])
        for fd in r:
            for event in devices[fd].read():
                if event.type == EV_KEY:
                    print(event)

    return None


def start_red_light_green_light(device: InputDevice) -> bool:
    print("Starting red light green")


def wait_for_input(devices: list[InputDevice], duration_seconds: int):
    print("TODO")


def get_ev_key_input_devices(vid: str, pid: str) -> list[InputDevice]:
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    key_input_devices: list[InputDevice] = []

    vid_int = int(vid, 16)
    pid_int = int(pid, 16)

    print("EV_KEY is" + str(EV_KEY))
    for device in devices:
        if device.info.vendor == vid_int and device.info.product == pid_int:
            # if device can press buttons
            if EV_KEY in device.capabilities():
                key_input_devices.append(device)

    return key_input_devices


if __name__ == "__main__":
    main()
