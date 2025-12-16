#!/usr/bin/env python3
"""
test_vm_mount.py
----------------
Test script for virtual USB stick mounting in VM.
Tests creation, host mounting, VM attachment, and cleanup.
"""

import sys
import time
import subprocess
from pathlib import Path
from vusb import VirtualUSBStick

# Test configuration
TEST_IMAGE = Path("/tmp/test_vusb.img")
QMP_SOCKET = "/tmp/securepass_qmp.sock"
DEVICE_ID = "test_vusb0"
SIZE_MB = 50

def print_step(step_num, description):
    """Print formatted test step"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {description}")
    print('='*60)

def check_qmp_socket():
    """Check if QMP socket exists (VM running)"""
    if not Path(QMP_SOCKET).exists():
        print(f"[ERROR] QMP socket not found: {QMP_SOCKET}")
        print("[INFO] Start the VM first with edit_base_image.py or host_daemon.py")
        return False
    print(f"[OK] QMP socket found: {QMP_SOCKET}")
    return True

def check_vm_mount():
    """Check if USB device is mounted in VM via SSH/console"""
    print("\n[INFO] To check in VM, run these commands:")
    print("# In der VM Konsole:")
    print("mkdir -p /mnt/test")
    print("# Direkt das Device mounten")
    print("mount -t vfat /dev/sdb /mnt/test")
    print("# Inhalt prüfen")
    print("ls -la /mnt/test")
    print("cat /mnt/test/test.txt")

def main():
    print("="*60)
    print("Virtual USB Stick Mount Test")
    print("="*60)
    
    # Clean up old test image
    if TEST_IMAGE.exists():
        print(f"[INFO] Removing old test image: {TEST_IMAGE}")
        TEST_IMAGE.unlink()
    
    # Step 1: Check if VM is running
    print_step(1, "Check if VM is running")
    if not check_qmp_socket():
        return 1
    
    # Step 2: Create virtual USB stick
    print_step(2, "Create virtual USB stick")
    vusb = VirtualUSBStick(
        image_path=TEST_IMAGE,
        size_mb=SIZE_MB,
        qmp_socket=QMP_SOCKET,
        device_id=DEVICE_ID
    )
    
    try:
        vusb.create(filesystem='vfat', label='TEST_USB')
        print("[OK] Virtual USB stick created")
    except Exception as e:
        print(f"[ERROR] Failed to create: {e}")
        return 1
    
    # Step 3: Mount on host and add test files
    print_step(3, "Mount on host and add test files")
    try:
        vusb.mount_on_host()
        print("[OK] Mounted on host")
        
        # Create test files
        test_file = Path(vusb.host_mount) / "test.txt"
        test_file.write_text("Hello from host!\nThis is a test file.\n")
        print(f"[OK] Created test file: {test_file}")
        
        # List files
        result = subprocess.run(
            ['ls', '-lh', vusb.host_mount],
            capture_output=True,
            text=True
        )
        print(f"[INFO] Host mount content:\n{result.stdout}")
        
        time.sleep(1)
        
    except Exception as e:
        print(f"[ERROR] Failed to mount on host: {e}")
        return 1
    
    # Step 4: Unmount from host
    print_step(4, "Unmount from host")
    try:
        vusb.unmount_from_host()
        print("[OK] Unmounted from host")
    except Exception as e:
        print(f"[ERROR] Failed to unmount: {e}")
        return 1
    
    # Step 5: Attach to VM
    print_step(5, "Attach to VM via QMP")
    try:
        vusb.attach_to_vm()
        print("[OK] Attached to VM")
        print("[INFO] USB device should now be visible in VM")
        
    except Exception as e:
        print(f"[ERROR] Failed to attach to VM: {e}")
        return 1
    
    # Step 6: Wait and show instructions
    print_step(6, "Manual verification in VM")
    check_vm_mount()
    
    input("\n[PAUSE] Press Enter after checking in VM to continue with cleanup...")
    
    # Step 7: Detach from VM
    print_step(7, "Detach from VM")
    try:
        vusb.detach_from_vm()
        print("[OK] Detached from VM")
    except Exception as e:
        print(f"[ERROR] Failed to detach: {e}")
        return 1
    
    # Step 8: Mount on host again to verify
    print_step(8, "Mount on host again to verify data")
    try:
        vusb.mount_on_host()
        print("[OK] Mounted on host")
        
        # Check if test file still exists
        test_file = Path(vusb.host_mount) / "test.txt"
        if test_file.exists():
            content = test_file.read_text()
            print(f"[OK] Test file still exists:\n{content}")
        else:
            print("[WARNING] Test file not found")
        
        # List all files
        result = subprocess.run(
            ['ls', '-lh', vusb.host_mount],
            capture_output=True,
            text=True
        )
        print(f"[INFO] Final content:\n{result.stdout}")
        
        vusb.unmount_from_host()
        print("[OK] Unmounted from host")
        
    except Exception as e:
        print(f"[ERROR] Failed final mount: {e}")
        return 1
    
    # Step 9: Cleanup
    print_step(9, "Cleanup")
    try:
        TEST_IMAGE.unlink()
        print(f"[OK] Removed test image: {TEST_IMAGE}")
    except Exception as e:
        print(f"[WARNING] Failed to remove test image: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("="*60)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
        sys.exit(130)
