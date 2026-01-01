#!/usr/bin/env python3

# ------------------------------------------------------------
# FIX SNAP/VSCODE ENV POLLUTION THAT BREAKS GTK/YAD
# ------------------------------------------------------------
import os

BAD_ENV_VARS = [
    "GTK_PATH",
    "LOCPATH",
    "GIO_MODULE_DIR",
    "GTK_IM_MODULE_FILE",
    "GTK_EXE_PREFIX",
    "XDG_DATA_DIRS",
    "XDG_DATA_HOME"
]

for var in BAD_ENV_VARS:
    if var in os.environ:
        #print(f"[ENV FIX] Removing polluted env var: {var}")
        os.environ.pop(var, None)


# ------------------------------------------------------------
# Normal imports AFTER cleanup
# ------------------------------------------------------------     
import subprocess
import time
import threading

# Configuration
POPUP_TIMEOUT = 30  # Auto-accept after 30 seconds


def show_delete_vusb_popup(mount_path):
    """
    Shows a popup asking if the temporary vUSB image should be deleted.
    Returns True if user accepts deletion.
    """
    
    message = (
        f"USB-Stick has been scanned!\n"
        f"All files are secure and you can access them safely.\n\n"
        f"<b>Mount Path:</b> {mount_path}\n\n"
        f"Do you want to delete the temporary vUSB image now?\n"
    )
    
    try:
        # Use yad with a timeout counter in the button
        result = subprocess.run(
            [
                "yad",
                "--question",
                "--title=USBeSafe - USB Device Scanned",
                "--text=" + message,
                "--width=400",
                "--button=Delete vUSB Image:0",
            ],
            capture_output=True
        )
        
        if result.returncode == 0:
            print("✅ User accepted deletion of vUSB image")
            return True
        else:
            print("❌ User declined deletion of vUSB image")
            return False
            
    except Exception as e:
        print(f"⚠️  Error showing popup: {e}, auto-accepting deletion")
        return True


def show_scan_popup(device_info):
    """
    Shows a popup asking if the USB device should be scanned.
    Auto-accepts after POPUP_TIMEOUT seconds with countdown.
    Returns True if user accepts (or timeout), False if user declines.
    
    Args:
        device_info: Dictionary with keys 'vid', 'pid', 'serial'
    
    Returns:
        bool: True if scan should proceed, False otherwise
    """
    vid = device_info.get('vid', 'Unknown')
    pid = device_info.get('pid', 'Unknown')
    vendor_name = device_info.get('vendor_name', 'Unknown')
    product_name = device_info.get('product_name', 'Unknown')
    serial = device_info.get('serial', 'N/A')
    
    message = (
        f"USB Mass Storage Device Detected!\n\n"
        f"<b>VID:</b> {vid}, {vendor_name}\n"
        f"<b>PID:</b> {pid}, {product_name}\n"
        f"<b>Serial:</b> {serial}\n\n"
        f"Do you want to scan this device in a secure VM?"
    )
    
    try:
        # Use yad with a timeout counter in the button
        result = subprocess.run(
            [
                "yad",
                "--question",
                "--title=USBeSafe - USB Device Detected",
                "--text=" + message,
                "--width=400",
                "--button=Scan Device:0",
                "--button=Skip:1",
                "--timeout=" + str(POPUP_TIMEOUT),
                "--timeout-indicator=bottom"
            ],
            capture_output=True
        )
        
        # Return codes: 0 = Scan, 1 = Skip, 70 = Timeout (treated as accept)
        if result.returncode in (0, 70):
            print("✅ User accepted scan (or timeout - auto-accepted)")
            return True
        else:
            print("❌ User declined scan")
            return False
            
    except Exception as e:
        print(f"⚠️  Error showing popup: {e}, auto-accepting scan")
        return True


def show_whitelist_popup(device_info):
    """
    Shows a popup that the detected usb device is not on the whitelist, asking if the USB device should be scanned.
    If accepted, the pc will be unavailable for a short period of time (the pci usb controller is passed to the vm)
    Auto-accepts after POPUP_TIMEOUT seconds with countdown.
    Returns True if user accepts (or timeout), False if user declines.

    Args:
        device_info: Dictionary with keys 'vid', 'pid', 'serial'

    Returns:
        bool: True if scan should proceed, False otherwise
    """
    vid = device_info.get('vid', 'Unknown')
    pid = device_info.get('pid', 'Unknown')
    vendor_name = device_info.get('vendor_name', 'Unknown')
    product_name = device_info.get('product_name', 'Unknown')
    serial = device_info.get('serial', 'N/A')

    message = (
        f"USB Device Is Not Registered On The Whitelist!\n\n"
        f"<b>VID:</b> {vid}, {vendor_name}\n"
        f"<b>PID:</b> {pid}, {product_name}\n"
        f"<b>Serial:</b> {serial}\n\n\n"
        f"Do you want to scan this device in a secure VM?\n\n"
        f"!!! YOUR COMPUTER WILL BE UNAVAILABLE FOR A SHORT PERIOD OF TIME AND YOU WILL NOT BE ABLE TO INTERACT WITH YOUR PC UNTIL THE SCAN IS FINISHED !!!\n\n"
        f"If declined, the usb device will stay unauthorized and you will not be able to access it.\n"
    )

    try:
        # Use yad with a timeout counter in the button
        result = subprocess.run(
            [
                "yad",
                "--question",
                "--title=USBeSafe - Device not registered",
                "--text=" + message,
                "--width=800",
                "--button=Scan Device:0",
                "--button=Don't scan device:1",
                "--timeout=" + str(POPUP_TIMEOUT * 2),
                "--timeout-indicator=bottom"
            ],
            capture_output=True
        )

        # Return codes: 0 = Scan, 1 = Skip, 70 = Timeout (treated as accept)
        if result.returncode in (0, 70):
            print("✅ User accepted scan (or timeout - auto-accepted)")
            return True
        else:
            print("❌ User declined scan")
            return False

    except Exception as e:
        print(f"⚠️  Error showing popup: {e}, auto-accepting scan")
        return True


class StatusWindow:
    """
    Manages a status window that shows the current scan progress.
    """
    
    def __init__(self, device_info):
        self.device_info = device_info
        self.process = None
        self.current_step = ""
        
    def start(self):
        """Start the status window in a separate thread."""
        thread = threading.Thread(target=self._run_status_window, daemon=True)
        thread.start()
        time.sleep(0.5)  # Give the window time to appear
        
    def update(self, step_message):
        """Update the status message."""
        self.current_step = step_message
        print(f"📊 Status: {step_message}")
        
        # Update the dialog text by writing to stdin
        if self.process and self.process.poll() is None:
            try:
                # For yad, send text update
                self.process.stdin.write(f"# {step_message}\n".encode())
                self.process.stdin.flush()
            except Exception as e:
                print(f"⚠️  Could not update status window: {e}")
    
        
    def close(self):
        """Close the status window."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
    
    def _run_status_window(self):
        """Run the status window (internal method)."""
        vid = self.device_info.get('vid', 'Unknown')
        pid = self.device_info.get('pid', 'Unknown')
        serial = self.device_info.get('serial', 'N/A')
        
        try:
            # Use yad progress dialog
            self.process = subprocess.Popen(
                [
                    "yad",
                    "--progress",
                    "--title=USBeSafe - Scanning USB Device",
                    "--text=Initializing scan...",
                    "--width=500",
                    "--height=150",
                    "--no-buttons",
                    "--pulsate",
                    "--auto-close"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"⚠️  Could not start yad status window: {e}")



import os

# Remove Snap/VSCode-injected environment variables that break GTK apps
for var in [
    "GTK_PATH",
    "LOCPATH",
    "GIO_MODULE_DIR",
    "GTK_IM_MODULE_FILE",
    "GTK_EXE_PREFIX",
    "XDG_DATA_DIRS",
    "XDG_DATA_HOME"
]:
    if var in os.environ:
        print(f"[WARN] Removing polluted env var: {var}")
        os.environ.pop(var, None)
