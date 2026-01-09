from select import select

import evdev
from evdev import ecodes, InputDevice
from evdev.ecodes import *

RELEVANT_KEYBOARD_KEYS = [KEY_A, KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J, KEY_L, KEY_M, KEY_N,
                          KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T, KEY_U, KEY_V, KEY_W, KEY_X, KEY_Y, KEY_Z,
                          KEY_0, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9,
                          KEY_ENTER, KEY_ESC, KEY_BACKSPACE, KEY_SPACE, KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTCTRL,
                          KEY_RIGHTALT, KEY_LEFTMETA, KEY_RIGHTMETA, KEY_LEFTSHIFT, KEY_RIGHTSHIFT, KEY_TAB, KEY_DOT,
                          KEY_COMMA, KEY_SEMICOLON, KEY_SLASH, KEY_BACKSLASH]


# Execute with sudo! otherwise can't list devices
def main():
    vid = "1532"
    pid = "008a"

    vid = "239a"
    pid = "80f4"

    devices = get_ev_key_input_devices(vid, pid)

    # device can't send key inputs -> OK!
    if len(devices) == 0:
        return True

    devices = {dev.fd: dev for dev in devices}

    while True:
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
    """
    Returns real keyboard devices. Checks if the device supports any of the listed typical keyboard keys.
    If yes, it has to be checked. If no, it has not to be checked.
    An empty list means that it has not to be checked
    """
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    vid_int = int(vid, 16)
    pid_int = int(pid, 16)

    key_input_devices: list[InputDevice] = []

    for device in devices:
        # find device matching the VID and PID
        if device.info.vendor == vid_int and device.info.product == pid_int:
            # if device can press buttons
            if EV_KEY in device.capabilities():
                # check if the device supports any of the relevant keyboard keys
                if any(key in set(device.capabilities()[EV_KEY]) for key in RELEVANT_KEYBOARD_KEYS):
                    key_input_devices.append(device)

    return key_input_devices


if __name__ == "__main__":
    main()
