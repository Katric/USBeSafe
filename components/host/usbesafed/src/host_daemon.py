#!/usr/bin/env python3

import os
import shutil
import subprocess
import time
import socket
from pathlib import Path
import pyudev
from pyudev import Monitor, Context

import popup
from vusb import VirtualUSBStick
from popup import show_delete_vusb_popup, show_scan_popup, StatusWindow
import manage_usb_ids
import check_and_load_bad_usb_config

# ---------------- CONFIG ----------------
VM_NAME_PREFIX = "alpine-usb-"

# Base image location (always correct regardless of where script is run)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_IMAGE = (SCRIPT_DIR / ".." / ".." / ".." / ".." / "images" / "alpine-base.qcow2").resolve()

# Overlay lives in the same directory as the base image
OVERLAY_IMAGE = BASE_IMAGE.parent / "overlay.qcow2"

QMP_SOCKET = "/tmp/securepass_qmp.sock"
VIRTIO_SOCKET = "/tmp/securepass_virtio.sock"

VUSB_IMMAGE = Path("/tmp/vusb.img")  # temporary vUSB image location


# ============================================================
#                      Dependencies Checker
# ============================================================

def check_system_deps():
    """Check for required system tools"""
    missing = []
    tools = {
        "qemu-system-x86_64": "qemu-system-x86",
        "qemu-img": "qemu-utils",
        "wget": "wget",
        "virsh": "virsh",
        "yad": "yad",
        "xterm": "xterm"
    }

    for tool, package in tools.items():
        if shutil.which(tool) is None:
            missing.append(package)

    if missing:
        print("USBeSafe startup check:\n")
        print(f"Missing system packages detected: {missing}\n")
        print("To install on Debian/Ubuntu, run:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-clients qemu-kvm wget curl yad xterm\n")
        print("Then re-run the daemon.\n")
        return False

    return True


# ============================================================
#                      Disable Auto-Mount
# ============================================================

def disable_udisks2_service(is_bad_usb_protection_active: bool):
    """
    Masks and stops udisks2.service to disable auto-mount.
    """

    return  # todo remove return after development is finished to disable udisks2
    # 1. systemctl mask udisks2.service
    mask_command = ["systemctl", "mask", "udisks2.service"]
    try:
        subprocess.run(mask_command, check=True, capture_output=True, text=True)
        print("✅ udisks2 successfully masked.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error when trying to mask udisks2. Code {e.returncode}: {e.stderr.strip()}")
        return False

    # 2. systemctl stop udisks2.service
    stop_command = ["systemctl", "stop", "udisks2.service"]
    try:
        subprocess.run(stop_command, check=True, capture_output=True, text=True)
        print("✅ udisks2 sucessfully stopped.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error when trying to stop udisks2. Code {e.returncode}: {e.stderr.strip()}")
        return False


def set_usb_default_authorization(enable: bool):
    """
    Iterates over all USB root hubs and sets the 'authorized_default' value.

    Args:
        enable (bool):
            If True, sets authorized_default to '1' (Auto-authorize new devices).
            If False, sets authorized_default to '0' (Do not authorize new devices).
    """
    base_path = Path("/sys/bus/usb/devices")

    # Determine the string value to write based on the boolean input
    target_value = "1" if enable else "0"
    state_desc = "ENABLED" if enable else "DISABLED"

    print(f"[INFO] Auto-authorization will be {state_desc} ({target_value})...")

    if not base_path.exists():
        print(f"[ERROR]: Path {base_path} does not exist. Are you using a Linux OS :D ?")
        return

    changed_count = 0

    # Iterate over all items in the directory
    for device_dir in base_path.iterdir():
        # Filter: We only want Root Hubs (e.g., usb1, usb2, usb10)
        # We ignore sub-devices like '1-1'
        if device_dir.name.startswith("usb") and device_dir.name[3:].isdigit():

            auth_file = device_dir / "authorized_default"

            if auth_file.exists():
                try:
                    # Read current value to check if an update is actually needed
                    current_val = auth_file.read_text().strip()

                    if current_val != target_value:
                        # Write the new value
                        auth_file.write_text(target_value)
                        print(
                            f"[OK] {device_dir.name}: authorized_default changed from {current_val} to {target_value}.")
                        changed_count += 1
                    else:
                        print(f"[INFO] {device_dir.name}: Already set to {target_value}.")

                except PermissionError:
                    print(f"[ERROR] Permission denied for {device_dir.name}. Please run with 'sudo'.")
                except Exception as e:
                    print(f"[ERROR] Failed to access {device_dir.name}: {e}")
            else:
                # Some controllers might not support this attribute
                print(f"[SKIP] {device_dir.name}: File 'authorized_default' not found.")

    print("-" * 40)
    print(f"[INFO] Done. Updated {changed_count} USB buses to {target_value}.")


# ============================================================
#                     OVERLAY CREATION
# ============================================================

def create_overlay():
    print("[INFO] Creating overlay…")

    if os.path.exists(OVERLAY_IMAGE):
        os.remove(OVERLAY_IMAGE)

    subprocess.run([
        "qemu-img", "create",
        "-f", "qcow2",  # <--- format of the new image
        "-F", "qcow2",  # <--- tell QEMU the backing image format
        "-b", str(BASE_IMAGE),
        str(OVERLAY_IMAGE)
    ], check=True)

    print("[INFO] Overlay created:", OVERLAY_IMAGE)


# ============================================================
#                     QEMU START
# ============================================================

def start_vm(vid, pid):
    """
    PRODUCTION VM:
    - headless
    - overlay as root disk
    - virtio-serial port for communication
    - QMP for control
    - pass through the real USB stick
    """

    print("[INFO] Starting scanning VM")
    # Check if KVM is available
    kvm_available = os.path.exists("/dev/kvm")

    # Remove old sockets
    for s in (QMP_SOCKET, VIRTIO_SOCKET):
        if os.path.exists(s):
            os.remove(s)
    try:
        qemu_cmd = [
            "qemu-system-x86_64",
            "-m", "1024",
            "-smp", "2",

            "-drive", f"file={OVERLAY_IMAGE},format=qcow2",

            "-nographic",

            # QEMU won’t bind to your TTY. good for debugging /remove to get access to VM
            # "-serial", "none",

            # --- Virtio communication channel ---
            "-chardev", f"socket,id=virtiocomm,path={VIRTIO_SOCKET},server=on,wait=off",
            "-device", "virtio-serial-pci",
            "-device", "virtserialport,chardev=virtiocomm,name=com.securepass.comm",

            # --- QMP channel ---
            "-qmp", f"unix:{QMP_SOCKET},server,nowait",
            "-usb",  # Enable USB
            # --- USB passthrough (real hardware) ---
            "-device", "qemu-xhci,id=xhci",
            "-device", f"driver=usb-host,bus=xhci.0,vendorid=0x{vid},productid=0x{pid}"
        ]

        if kvm_available:
            qemu_cmd.insert(1, "-enable-kvm")
            print("[INFO] KVM acceleration enabled")
        else:
            print("[WARNING] KVM not available, using software emulation (slower)")

        terminal_cmd = ["xterm", "-title", "VM Output", "-e"]
        final_cmd = terminal_cmd + qemu_cmd

        print("[INFO] Launching QEMU in new terminal:")
        print(" ".join(qemu_cmd))

        vm_process = subprocess.Popen(final_cmd)

        print(f"[+] VM started (PID: {vm_process.pid})")

        time.sleep(1)
        return vm_process

    except Exception as e:
        raise Exception(f"Failed to spawn QEMU: {e}")


# ============================================================
#                     VIRTIO MESSAGE RECV
# ============================================================

def wait_for_virtio():
    print("[INFO] Waiting for VM daemon messages…")

    # Wait for virtio socket
    while not os.path.exists(VIRTIO_SOCKET):
        time.sleep(0.2)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(VIRTIO_SOCKET)

        while True:
            data = s.recv(1024).decode().strip()
            if data:
                print(f"[VM → HOST] {data}")
                return data


# ============================================================
#                      QMP CONTROL
# ============================================================

def qmp_send(cmd):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(QMP_SOCKET)
            time.sleep(0.2)
            s.recv(4096)  # QMP greeting
            s.send((cmd + "\n").encode())
            return s.recv(4096).decode()
    except:
        return None


def kill_vm(vm):
    print("[INFO] Stopping VM…")
    try:
        qmp_send('{ "execute": "system_powerdown" }')
        vm.wait(timeout=5)
    except:
        print("[WARN] Hard kill")
        vm.kill()


def cleanup_overlay():
    if os.path.exists(OVERLAY_IMAGE):
        print("[INFO] Removing overlay:", OVERLAY_IMAGE)
        os.remove(OVERLAY_IMAGE)


# ============================================================
#                    EXISTING USB LISTENER
# ============================================================

# Only for debug purposes
def is_usb_device_a_mass_storage(device) -> bool:
    is_mass_storage = False
    try:
        print("[DEBUG] Checking if usb device is a mass storage")
        for child in device.children:
            if (child.get('DEVTYPE') == 'usb_interface' and
                    child.get('DRIVER') == 'usb-storage'):
                is_mass_storage = True
                break
    except Exception as e:
        print("[DEBUG] Error while gathering information of usb device: ", e)
    return is_mass_storage


def set_usb_autoprobe(enabled: bool):
    """Activates or deactivates driver_autoprobe"""
    try:
        val = "1" if enabled else "0"
        with open("/sys/bus/usb/drivers_autoprobe", "w") as f:
            f.write(val)
        if enabled:
            print("[INFO] USB autoprobe enabled")
        else:
            print("[INFO] USB autoprobe disabled")
    except Exception as e:
        print(f"[ERROR] Could not set driver_autoprobe: {e}")


def set_authorize_device(device_sys_path, enable: bool) -> bool:
    """
    Activates or deactivates authorization
    :param device_sys_path: The path to the device
    :param enable: Whether to enable or disable authorization
    :returns: True or False if setting the authorization value was successful
    """
    try:
        val = "1" if enable else "0"
        auth_path = os.path.join(device_sys_path, "authorized")
        with open(auth_path, "w") as f:
            f.write(val)
        if val:
            print(f"[INFO] Successfully authorized device {device_sys_path}")
        else:
            print(f"[INFO] Successfully unauthorized device {device_sys_path}")
        return True
    except Exception as e:
        print(f"[Error] An error occurred during authorization: {e}")
        return False


def safe_authorize_device(device_sys_path):
    """
    Authorizes the device but deactivates driver_autoprobe before, so no drivers are loaded on the host.
    Also sets bConfigurationValue of this device to 1.
    """
    print(f"[INFO] Deactivating driver_autoprobe globally and authorizing device: {device_sys_path}")
    set_usb_autoprobe(False)
    if set_authorize_device(device_sys_path,True):
        time.sleep(0.5)  # wait a little
    else:
        print("Reactivating driver_autoprobe...")
        set_usb_autoprobe(True)
        return False

    try:
        config_path = os.path.join(device_sys_path, "bConfigurationValue")

        with open(config_path, "w") as f:
            f.write("1")

        print(f"[INFO] Device {device_sys_path} bConfigurationValue configured (Active Config=1)")
        time.sleep(0.5)  # wait a little
    except Exception as e:
        print(f"ERROR: Could not set configuration: {e}")
        return False

    return True


def handle_add_usb(is_bad_usb_protection_active: bool):
    """
    Listens to ADD udev events and reads the following properties:
    - VID
    - PID
    - Serial Number (if present)
    - Path
    - Is mass storage device

    Shows popup, creates status window, then runs the full
    production scanning pipeline (overlay, virtio, QMP, OK/FAIL, copy_done).
    """

    context: Context = pyudev.Context()
    monitor: Monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("=" * 60)
    print("Waiting for new USB Devices... (Event type ADD)")
    print("=" * 60)

    for device in iter(monitor.poll, None):
        device: pyudev.Device = device

        # --- Check correct event type ---
        if device is None or device.action != 'add':
            continue

        ############### SEE DEVICE ATTRIBUTES ###############
        # for key, value in device.items():
        #    print(f"  {key:<20}: {value}")

        print(f"[INFO] {device} connected")

        # --- Only parent USB device ---
        if device.get('DEVTYPE') != 'usb_device':
            print(f"Device type is {device.get('DEVTYPE')}. Skipping.")
            continue

        print(f"[INFO] Safe wakeup of {device.device_path}...")

        # --- VID/PID extraction ---
        vid = device.get('ID_VENDOR_ID', None)
        pid = device.get('ID_MODEL_ID', None)
        serial = device.get('ID_SERIAL_SHORT', device.get('ID_SERIAL', None))
        # TODO get usb storage size

        if vid is None or pid is None:
            print("[Warning] Cannot identify usb device")
            print("[Warning] Device does not provide a vendor id and / or a product id. Skipping.")
            continue

        # Extract human-readable vendor and product names from vid and pid
        vendor_name, product_name = manage_usb_ids.get_vendor_and_product_names(device)

        # Wait briefly for kernel to finish setting up children
        time.sleep(2)

        # FOR DEBUG --> Should not be possible to return a result
        is_mass_storage = is_usb_device_a_mass_storage(device)

        print("\n✅ New USB Device detected!")
        print("-" * 40)
        print(f"  VID               : {vid}, {vendor_name}")
        print(f"  PID               : {pid}, {product_name}")
        print(f"  Serial Number     : {serial}")
        print(f"  Path              : {device.device_path}")
        print(f"  Is mass storage   : {is_mass_storage}")
        print("-" * 40)
        print("\n")

        device_info = {"vid": vid, "vendor_name": vendor_name, "pid": pid, "product_name": product_name,
                       "serial": serial}

        # check if usb device is already on the whitelist
        device_hash_for_whitelisting = manage_usb_ids.get_hashed_device_attributes(device)
        is_on_whitelist = manage_usb_ids.is_device_whitelisted(device_hash_for_whitelisting)
        if is_on_whitelist:
            print("[Info] Device is present on the whitelist.")
            print(f"[Info] Authorize device {device.sys_path}...")
            set_authorize_device(device.sys_path, True)
            print("[OK] Check complete. Device can now be used on the host system")
            # TODO: Ist das schon alles?
            continue

        else:
            print("[Warning] Device is NOT present on the whitelist and needs to be scanned.")
            # If 'scan'         ->  pass PCI Controller to VM
            # Else 'don't scan' ->  reject USB device and let it stay unauthorized

            if not popup.show_whitelist_popup(device_info):
                print("🚫 Scan cancelled by user")
                continue

            print("[Info] Scan accepted by user (or auto-timeout). Device will be passed to VM for secure scanning...")
            # TODO: implement forwarding PCI controller to VM
            # deactivate device_autoprobe and then authorize this device
            safe_authorize_device(device.sys_path)

            status_window = StatusWindow(device_info)
            status_window.start()
            status_window.update("Building VM configuration...")
            try:
                status_window.update("Preparing VM overlay and starting headless VM...")

                # --- Full Script 3 Logic (overlay + virtio + QMP) ---
                run_prod_scan(vid, pid, status_window)

            except Exception as e:
                status_window.update(f"Error: {str(e)}")
                print(f"[ERROR] Exception during VM scan: {e}")
                time.sleep(3)
                status_window.close()
                raise

            # manage_usb_ids.add_to_whitelist_file(device_hash_for_whitelisting)    # <-- registers an usb stick to the whitelist

# ============================================================
#                       USB LOGIC
# ============================================================

def run_prod_scan(vid, pid, status_window):
    """
    Runs the ENTIRE Script 3 logic:
    - Overlay creation
    - Start VM
    - virtio messaging
    - OK / FAIL handling
    - Wait for copy_done
    - Shutdown
    - Cleanup
    """
    create_overlay()
    vm = start_vm(vid, pid)

    # ---------------- FIRST MESSAGE (OK or FAIL) ----------------
    result = wait_for_virtio()

    if result == "fail":
        status_window.update("Scan FAILED, malware detected!")
        kill_vm(vm)
        cleanup_overlay()
        return

    if result == "ok":
        status_window.update("Scan clean, waiting for copy…")
        # ---------------- SECOND MESSAGE (USB SIZE) ----------------
        real_usb_size_gb = wait_for_virtio()
        if not real_usb_size_gb.isdigit():
            status_window.update("Error: Invalid USB size received from VM.")
            kill_vm(vm)
            cleanup_overlay()
            return
        status_window.update(f"Preparing vUSB of size {real_usb_size_gb} GB...")
        vUSB = VirtualUSBStick(image_path=VUSB_IMMAGE, size_mb=int(real_usb_size_gb) * 1024, qmp_socket=QMP_SOCKET,
                               device_id="vusb")
        try:
            vUSB.create(filesystem='vfat', label='USBeSafe')
            vUSB.attach_to_vm()
            status_window.update("vUSB attached to VM, waiting for copy…")
        except Exception as e:
            status_window.update(f"Error setting up vUSB: {e}")
            kill_vm(vm)
            cleanup_overlay()
            return
        # ---------------- WAIT FOR "copy_done" ----------------
        msg = wait_for_virtio()
        if msg == "copy_done":
            status_window.update("Copy completed.")
            time.sleep(2)
            vUSB.detach_from_vm()
            status_window.update("Shutting down VM…")
            kill_vm(vm)
            cleanup_overlay()
            vUSB.mount_on_host()
            status_window.update(f"vUSB mounted on host at {vUSB.host_mount}")

            if show_delete_vusb_popup(vUSB.host_mount):
                vUSB.unmount_from_host()
                os.remove(vUSB.image_path)
                status_window.update("Temporary vUSB image deleted.")
            else:
                status_window.update("Temporary vUSB image kept.")

            return

    # unknown
    status_window.update("Unknown VM message.")
    kill_vm(vm)
    cleanup_overlay()


def is_bad_usb_protection_active() -> bool:
    # load usbesafe config file and extract necessary keys
    usbesafe_config = check_and_load_bad_usb_config.load_usbesafe_config()
    is_active: bool = usbesafe_config.get(check_and_load_bad_usb_config.BAD_USB_PROTECTION, 0)
    return is_active


# ============================================================
#                       MAIN
# ============================================================

def main():
    print("=== USBeSafe Daemon, Production Mode ===")

    # Check dependencies
    if not check_system_deps():
        return

    # ########## To Restore functionality xD ##########
    # set_usb_default_authorization(True)
    # set_usb_autoprobe(True)
    # # Disable 'authorized_default' values on all usb bus systems
    set_usb_default_authorization(False)
    is_protection_active: bool = is_bad_usb_protection_active()
    disable_udisks2_service(is_protection_active)  # disable and mask udisks2 to disable automount
    handle_add_usb(is_protection_active)


if __name__ == "__main__":
    main()
