import random
import time
from select import select

import evdev
from evdev import InputDevice
from evdev.ecodes import *

import host_communication

RELEVANT_KEYBOARD_KEYS = [KEY_A, KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J, KEY_L, KEY_M, KEY_N,
                          KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T, KEY_U, KEY_V, KEY_W, KEY_X, KEY_Y, KEY_Z,
                          KEY_0, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9,
                          KEY_ENTER, KEY_ESC, KEY_BACKSPACE, KEY_SPACE, KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTCTRL,
                          KEY_RIGHTALT, KEY_LEFTMETA, KEY_RIGHTMETA, KEY_LEFTSHIFT, KEY_RIGHTSHIFT, KEY_TAB, KEY_DOT,
                          KEY_COMMA, KEY_SEMICOLON, KEY_SLASH, KEY_BACKSLASH]

BAD_USB_CHECK_GREEN = "BAD_USB_CHECK_GREEN"
BAD_USB_CHECK_RED = "BAD_USB_CHECK_RED"


def start_red_light_green_light(vid: str, pid: str) -> bool:
    """
    Starts a Challenge-Response red light green light game,
    if the requested device supports keyboard capabilities (like KEY_A, KEY_LEFTCTRL, etc.).
    :param vid: VendorID of the device
    :param pid: ProductID of the device
    :return: True, if BadUSB Checks are OK. False if not.
    """
    print("[INFO] Preparing red-light green-light BadUSB-Check")
    devices: list[InputDevice] = get_ev_key_input_devices(vid, pid)

    if len(devices) == 0:
        print(f"[INFO] Device does not report keyboard capabilities. Does not have to be BadUSB-checked.")
        return True

    print(f"[INFO] Device reports keyboard capabilities. Has to be BadUSB-checked.")

    is_first_round = True
    for i in range(1, 4):  # 3 rounds
        print(f"[INFO] Starting round {i}/3...")

        # GREEN PHASE
        duration = random.uniform(5.0, 10.0)
        if is_first_round:
            # extra time in first round so user can prepare
            duration = 15
        print(f"[INFO] Green phase is {duration} seconds. One input has to be sent.")

        flush_input(devices)
        host_communication.send_to_host(BAD_USB_CHECK_GREEN)
        input_detected = wait_for_input(devices, duration)

        if not input_detected:
            print(f"[INFO] No input received during green phase ({duration} s). BadUSB-Check failed.")
            return False
        elif input_detected:
            print("[INFO] Received input during green phase.")

        # RED PHASE
        duration = random.uniform(3.0, 10.0)
        print(f"[INFO] Red phase is {duration} seconds. No input must be sent.")

        time.sleep(0.5)
        flush_input(devices)
        host_communication.send_to_host(BAD_USB_CHECK_RED)
        illegal_input = wait_for_input(devices, duration)

        if illegal_input:
            print(f"[INFO] Received input during red phase ({duration} s). BadUSB-Check failed.")
            return False
        elif not illegal_input:
            print(f"[INFO] Did not receive any input during red phase ({duration} s). Phase passed.")

    print(f"Device {vid} {pid} has passed the BadUSB Checks.")
    return True


def wait_for_input(devices: list[InputDevice], duration_seconds: float):
    """
    Waits max. duration_seconds seconds for input. Returns earlier if input was received.
    :param devices: List of InputDevices to listen to
    :param duration_seconds: duration of secs to listen to
    Return: True, if input was received during the time. False if not.
    """
    start_time = time.time()
    fd_to_devices = {dev.fd: dev for dev in devices}

    while (time.time() - start_time) < duration_seconds:
        remaining_time = duration_seconds - (time.time() - start_time)
        if remaining_time <= 0:
            break

        r, _, _ = select(fd_to_devices.keys(), [], [], remaining_time)

        for fd in r:
            for event in fd_to_devices[fd].read():
                if event.type == EV_KEY:
                    return True

    return False


def flush_input(devices: list[InputDevice]):
    """
    Reads all the remaining data. Works like a "flush"
    """
    fd_to_devices = {dev.fd: dev for dev in devices}
    while True:
        r, _, _ = select(fd_to_devices.keys(), [], [], 0.0)  # 0.0 means dont wait

        if not r:
            break  # empty

        for fd in r:
            try:
                list(fd_to_devices[fd].read())
            except OSError:
                pass


def get_ev_key_input_devices(vid: str, pid: str) -> list[InputDevice]:
    """
    Returns real keyboard devices. Checks if the device supports any of the listed typical keyboard keys.
    If yes, it has to be checked. If no, it has not to be checked.
    An empty list means that it has not to be checked
    """
    print(f"[INFO] Checking if device {vid}:{pid} reports Keyboard Input capabilities...")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    vid_int = int(vid, 16)
    pid_int = int(pid, 16)

    key_input_devices: list[InputDevice] = []

    has_keyboard_capabilities = False  # has the device with vid and pid combination keyboard caps?
    for device in devices:
        # find device matching the VID and PID
        if device.info.vendor == vid_int and device.info.product == pid_int:
            # if device can press buttons
            if EV_KEY in device.capabilities():
                key_input_devices.append(device)
                # check if the device supports any of the relevant keyboard keys
                if any(key in set(device.capabilities()[EV_KEY]) for key in RELEVANT_KEYBOARD_KEYS):
                    print(f"[INFO] Device reports keyboard capabilities: {device}")
                    has_keyboard_capabilities = True

    if not has_keyboard_capabilities:
        return []

    return key_input_devices
