#!/usr/bin/env python3

import os
import shutil
import subprocess
import time

import pyudev
from pyudev import Context, Monitor

from popup import show_scan_popup, StatusWindow

SCRIPT_FILE_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_FILE_PATH)
BASE_IMAGE_REL_TO_SCRIPT = os.path.join('..', '..', '..', '..', 'images', 'alpine-base.qcow2')

# ---- CONFIG ----
VM_NAME_PREFIX = "alpine-usb-"
# QCOW2_BASE_IMAGE = "../../../../images/alpine-base.qcow2"
QCOW2_BASE_IMAGE_SOURCE = os.path.normpath(os.path.join(SCRIPT_DIR, BASE_IMAGE_REL_TO_SCRIPT))
VM_DISK_DIR = "/var/lib/libvirt/images/"
QCOW2_BASE_IMAGE = os.path.join(VM_DISK_DIR, "alpine-base.qcow2")
VM_RAM = 1024
VM_VCPUS = 1
VM_BRIDGE = "virbr0"



def create_vm_disk(vm_id):
    """
    Creates Copy-on-Write QCOW2 image, cloned from base img
    """
    if not os.path.exists(QCOW2_BASE_IMAGE):
        print(f"❌ Error: Could not find base img under {QCOW2_BASE_IMAGE}")
        return None

    vm_disk_path = os.path.join(VM_DISK_DIR, f"{VM_NAME_PREFIX}{vm_id}-disk.qcow2")

    try:
        print(f"➡️ Clone base img for VM: {vm_disk_path}")
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f", "qcow2",
                "-o", f"backing_file={QCOW2_BASE_IMAGE},backing_fmt=qcow2",
                vm_disk_path
            ],
            check=True
        )
        return vm_disk_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating QCOW2 overlay: {e}")
        return None


def build_vm_xml(vm_name, vm_disk_path, usb_vendor_id, usb_product_id):
    """
    Generates VM config with USB-Passthrough.
    """
    # Check if KVM is available, otherwise fall back to QEMU emulation
    virt_type = 'kvm' if os.path.exists('/dev/kvm') else 'qemu'
    
    # Destroyed on poweroff
    xml = f"""
        <domain type='{virt_type}'>
          <name>{vm_name}</name>
          <memory unit='MiB'>{VM_RAM}</memory>
          <vcpu placement='static'>{VM_VCPUS}</vcpu>
          <os>
            <type arch='x86_64' machine='pc-q35-8.1'>hvm</type>
          </os>
          <features>
            <acpi/>
          </features>
          <on_poweroff>destroy</on_poweroff>
          <on_crash>destroy</on_crash>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='{vm_disk_path}'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            <interface type='bridge'>
              <source bridge='{VM_BRIDGE}'/>
              <model type='virtio'/>
            </interface>
            <graphics type='spice' autoport='yes'/>
            <controller type='usb' model='qemu-xhci'/>
        
            <hostdev mode='subsystem' type='usb'>
              <source>
                <vendor id='0x{usb_vendor_id}'/>
                <product id='0x{usb_product_id}'/>
              </source>
            </hostdev>
        
          </devices>
        </domain>
    """
    return xml.strip()


def start_transient_vm(vm_name, vm_xml):
    """Starts a transient VM using virsh create."""
    try:
        print(f"🔥 Starting transient VM: **{vm_name}**...")
        subprocess.run(
            ["virsh", "create", "/dev/stdin"],
            input=vm_xml.encode('utf-8'),
            check=True
        )
        print(f"✅ VM '{vm_name}' started. USB device passed over to VM.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting the VM: '{vm_name}' with virsh: {e}")
        return False


def handle_add_usb():
    """
    Listens to ADD udev events and reads the following properties:
    - VID
    - PID
    - Serial Number (if present)
    - Path
    - Is mass storage device

    Starts VM and attaches a connected USB device (if it is mass storage) to the started VM
    """
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
            # TODO try shorter time
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

            if is_mass_storage:
                # Show popup and ask user if device should be scanned
                device_info = {
                    'vid': vid,
                    'pid': pid,
                    'serial': serial
                }
                
                if not show_scan_popup(device_info):
                    print("🚫 Scan cancelled by user")
                    continue
                
                # Create status window to show scan progress
                status_window = StatusWindow(device_info)
                status_window.start()
                
                try:
                    vm_id = os.urandom(4).hex()
                    vm_name = f"{VM_NAME_PREFIX}{vm_id}"

                    status_window.update("Creating VM disk image...")
                    vm_disk_path = create_vm_disk(vm_id)
                    if not vm_disk_path:
                        status_window.update("Error: Could not create QCOW2 image")
                        time.sleep(3)
                        status_window.close()
                        print("Error: Could not create QCOW2 image")
                        return

                    status_window.update("Building VM configuration...")
                    vm_xml = build_vm_xml(vm_name, vm_disk_path, vid, pid)

                    status_window.update("Starting VM and attaching USB device...")
                    if start_transient_vm(vm_name, vm_xml):
                        status_window.update("VM started successfully - Scanning USB device...")
                        print("VM started and USB passed")
                        # Keep status window open while VM is running
                        time.sleep(5)  # Show success message briefly
                        status_window.update("Scan in progress - VM is running...")
                        # TODO: Monitor VM status and update accordingly
                        # TODO temporary QCOW file has to be deleted manually after shutdown under vm_disk_path
                    else:
                        status_window.update("Error: Failed to start VM")
                        time.sleep(3)
                        status_window.close()
                except Exception as e:
                    status_window.update(f"Error: {str(e)}")
                    time.sleep(3)
                    status_window.close()
                    raise


def disable_udisks2_service():
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


def check_system_deps():
    """Check for required system tools"""
    missing = []
    tools = {
        "qemu-system-x86_64": "qemu-system-x86",
        "qemu-img": "qemu-utils",
        "wget": "wget",
        "virsh": "virsh",
        "yad": "yad"
    }

    for tool, package in tools.items():
        if shutil.which(tool) is None:
            missing.append(package)

    if missing:
        print("USBeSafe startup check:\n")
        print(f"Missing system packages detected: {missing}\n")
        print("To install on Debian/Ubuntu, run:")
        print("  sudo apt-get update")
        print("  sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-clients qemu-kvm wget curl yad\n")
        print("Then re-run the daemon.\n")
        return False

    return True


def ensure_base_image():
    """
    Ensure base image exists in libvirt images directory.
    Copy it from source location if needed.
    """
    if os.path.exists(QCOW2_BASE_IMAGE):
        print(f"✅ Base image already present: {QCOW2_BASE_IMAGE}")
        return True
    
    if not os.path.exists(QCOW2_BASE_IMAGE_SOURCE):
        print(f"❌ Error: Base image not found at {QCOW2_BASE_IMAGE_SOURCE}")
        return False
    
    try:
        print(f"📋 Copying base image to libvirt directory...")
        print(f"   From: {QCOW2_BASE_IMAGE_SOURCE}")
        print(f"   To:   {QCOW2_BASE_IMAGE}")
        shutil.copy2(QCOW2_BASE_IMAGE_SOURCE, QCOW2_BASE_IMAGE)
        os.chmod(QCOW2_BASE_IMAGE, 0o644)
        print(f"✅ Base image copied successfully")
        return True
    except Exception as e:
        print(f"❌ Error copying base image: {e}")
        return False


def main():
    print("╔════════════════════════════════════════════╗")
    print("║   USBeSafe Daemon - Secure USB Scanning   ║")
    print("╚════════════════════════════════════════════╝\n")

    # Check dependencies
    if not check_system_deps():
        return

    # Ensure base image is accessible to libvirt
    if not ensure_base_image():
        return

    disable_udisks2_service()  # disable and mask udisks2 to disable automount
    handle_add_usb()  # Listener listening for udev ADD events and starting VMs


if __name__ == "__main__":
    main()
