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
        # print(f"[ENV FIX] Removing polluted env var: {var}")
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
        f"USB Device Detected!\n\n"
        f"<b>VID:</b> {vid}, {vendor_name}\n"
        f"<b>PID:</b> {pid}, {product_name}\n"
        f"<b>Serial:</b> {serial}\n\n"
        f"Do you want to scan this device in a secure environment?\n"
        f"USB storage devices must be scanned each time before they can be accessed.\n\n"
        f"If declined, the device will remain unauthorized and cannot be used."
    )

    try:
        # Use yad with a timeout counter in the button
        result = subprocess.run(
            [
                "yad",
                "--question",
                "--title=USBeSafe - USB Device Detected",
                "--text=" + message,
                "--width=550",
                "--button=Scan Device:0",
                "--button=Don't Scan:1",
                "--timeout=" + str(POPUP_TIMEOUT),
                "--timeout-indicator=bottom"
            ],
            capture_output=True
        )

        # Return codes: 0 = Scan, 1 = Don't Scan, 70 = Timeout (treated as accept)
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


class BadUsbCheckWindow:
    """
    Popup for Bad USB checks. Starts at green and shows a progress bar.
    """

    static_message = [
        "Your device reports, that it is able to send keyboard inputs.\n",
        "<b>Be careful: Should it be able to do this?</b>\n\n",
        "If yes, follow the displayed instructions in green or red.\n"
    ]

    # total steps incl, start at 1
    def __init__(self, total_steps=6):
        self.total_steps = total_steps
        self.current_step = 0
        self.process = None
        self.canceled = False

    def start(self):
        self.current_step = 0
        self._show_window()

    def next(self):
        self.current_step += 1
        self._show_window()

    def close(self):
        self._kill_current_process()
        self.process = None

    def _kill_current_process(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None

    def _show_window(self):
        self._kill_current_process()

        percent = int((self.current_step / self.total_steps) * 100)
        if percent > 100: percent = 100

        if self.current_step % 2 != 0:
            status_text = "<span foreground='green' size='xx-large' weight='bold'>PRESS ONE BUTTON</span>"
        else:
            status_text = "<span foreground='red' size='xx-large' weight='bold'>DO NOT PRESS ANY BUTTONS</span>"

        additional_line = ""
        show_15_s_hint = self.current_step == 1
        if show_15_s_hint:
            additional_line = "\n\nThis window will close after 15 seconds and the device will be blocked if no buttons are pressed!\n"

        # Statischer Header
        header = f"<b>BadUSB Security Check</b>\nStep {self.current_step} of {self.total_steps}\n"
        full_text = f"{header}\n\n{"".join(self.static_message)}{additional_line}\n\n\n{status_text}"

        cmd = [
            "yad",
            "--progress",
            "--title=USBeSafe - Security Alert: Keyboard detected!",
            "--width=600",
            "--center",  # Zentriert, damit es nicht springt
            "--on-top",
            "--no-buttons",
            "--markup",  # Aktiviert HTML-Farben
            "--text-align=center",
            f"--text={full_text}",
            f"--percentage={percent}",
            "--auto-close"  # Optional, falls es bei 100% von selbst zugehen soll
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"Error opening yad window: {e}")

    def _send_update(self, percent, message):
        """Sendet Daten an die yad Pipe."""
        if self.process and self.process.poll() is None:
            try:
                # 1. Send Percentage
                self.process.stdin.write(f"{percent}".encode())

                # 2. Send Text (Prefix with # for YAD)
                self.process.stdin.write(f"# {message}\n".encode())

                self.process.stdin.flush()
            except BrokenPipeError:
                print("❌ Pipe broken. User likely clicked Cancel.")
                self.canceled = True
            except Exception as e:
                print(f"Error updating window: {e}")
        else:
            self.canceled = True


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
