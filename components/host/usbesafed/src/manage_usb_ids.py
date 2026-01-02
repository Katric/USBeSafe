import hashlib
import os
import time
import requests
import gzip
import shutil

# --- Configuration & Path Setup ---

# determine the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# calculate the path to the 'files' directory
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
FILES_DIR = os.path.join(PROJECT_ROOT, "files")
# define the full path to the usb.ids file
USB_IDS_FILEPATH = os.path.join(FILES_DIR, "usb.ids")
# define the full path to the whitelist.txt file
WHITELIST_FILEPATH = os.path.join(FILES_DIR, "whitelist.txt")

USB_IDS_URL = "http://www.linux-usb.org/usb.ids.gz"
DOWNLOAD_THRESHOLD_SECONDS = 7 * 24 * 60 * 60  # 7 days in seconds


def download_usb_ids_conditionally():
    """
    Downloads the compressed .gz file only if the local usb.ids is older
    than 7 days or does not exist. It automatically extracts the file.

    Returns:
        bool: True if the file is available (newly downloaded or cached), False on error.
    """

    # Ensure the target directory exists
    if not os.path.exists(FILES_DIR):
        print(f"[Setup] Directory '{FILES_DIR}' does not exist. Creating it...")
        try:
            os.makedirs(FILES_DIR, exist_ok=True)
        except OSError as e:
            print(f"[Error] Could not create directory '{FILES_DIR}': {e}")
            return False

    # check if the target file exists
    if os.path.exists(USB_IDS_FILEPATH):
        file_age = time.time() - os.path.getmtime(USB_IDS_FILEPATH)

        # check if cache is still valid (not older than 7 days)
        if file_age < DOWNLOAD_THRESHOLD_SECONDS:
            days_old = file_age / (24 * 60 * 60)
            print(f"[Cache] Local file '{USB_IDS_FILEPATH}' is only {days_old:.2f} days old. Download skipped.")
            return True
        else:
            print(f"[Download] File is older than 7 days. Downloading new version.")
    else:
        print(f"[Download] Local file '{USB_IDS_FILEPATH}' not found. Starting download.")

    # --- Download Logic with Gzip ---

    # store temp file in the same folder
    temp_gz_filepath = os.path.join(FILES_DIR, "temp_usb.ids.gz")

    try:
        print(f"[*] Connecting to {USB_IDS_URL}...")
        response = requests.get(USB_IDS_URL, stream=True, timeout=10)
        response.raise_for_status()

        # download compressed file
        with open(temp_gz_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[*] Download complete. Extracting to '{USB_IDS_FILEPATH}'...")

        # extract downloaded file
        with gzip.open(temp_gz_filepath, 'rb') as f_in:
            with open(USB_IDS_FILEPATH, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # remove temporarily .gz file
        os.remove(temp_gz_filepath)

        # update timestamp of extracted file to "now"
        os.utime(USB_IDS_FILEPATH, None)

        print(f"[Success] New list successfully saved to '{USB_IDS_FILEPATH}'.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[Error] Network error during download: {e}")
        if os.path.exists(temp_gz_filepath):
            os.remove(temp_gz_filepath)
        return False
    except OSError as e:
        print(f"[Error] Issue during extraction or file saving: {e}")
        if os.path.exists(temp_gz_filepath):
            os.remove(temp_gz_filepath)
        return False


def parse_usb_ids():
    """
    Reads the usb.ids file from the specific 'files' directory into a dictionary.
    """
    usb_db = {}
    current_vendor = None

    if not os.path.exists(USB_IDS_FILEPATH):
        print(f"[Error] File '{USB_IDS_FILEPATH}' not found. Cannot parse.")
        return {}

    print(f"[*] Parsing database from '{USB_IDS_FILEPATH}'...")

    # use 'latin-1' for encoding instead of utf-8
    try:
        with open(USB_IDS_FILEPATH, 'r', encoding='latin-1', errors='replace') as f:
            for line in f:
                if not line.strip() or line.startswith('#'):
                    continue

                # Vendor (0 tabs)
                if not line.startswith('\t'):
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2 and len(parts[0]) == 4:
                        vid, name = parts
                        current_vendor = vid
                        usb_db[vid] = {"name": name.strip(), "products": {}}

                # Product (1 tab)
                elif line.startswith('\t') and not line.startswith('\t\t') and current_vendor:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        pid, name = parts
                        usb_db[current_vendor]["products"][pid] = name.strip()
    except IOError as e:
        print(f"[Error] Could not read file: {e}")
        return {}

    return usb_db


def get_vendor_and_product_names(device):
    # download usb.ids if not already done
    download_usb_ids_conditionally()
    # parse ids into dictionary
    usb_ids_dictionary = parse_usb_ids()

    vid = device.get('ID_VENDOR_ID')
    pid = device.get('ID_MODEL_ID')

    # in case vid and pid have capital letters inside hex code
    if vid: vid = vid.lower()
    if pid: pid = pid.lower()

    # get vendor name and product name to be displayed
    vendor_entry = usb_ids_dictionary.get(vid)
    vendor_source = "Device"
    product_source = "Device"
    vendor_name = device.get('ID_VENDOR_FROM_DATABASE', "Unknown")
    product_name = device.get('ID_MODEL', "Unknown")

    if vendor_entry:
        # check if name is present in the dictionary
        if "name" in vendor_entry:
            vendor_name = vendor_entry["name"]
            vendor_source = "usb.ids"

        # check if pid is present in the dictionary
        if pid in vendor_entry["products"]:
            product_name = vendor_entry["products"][pid]
            product_source = "usb.ids"

    print(f"Got vendor: {vendor_name} (Source: {vendor_source})")
    print(f"Got product: {product_name} (Source: {product_source})")

    return vendor_name, product_name


def get_hashed_device_attributes(device) -> str:
    """
    Creates a unique ID for the usb device.
    The ID is generated by the device's attributes. If a serial number is present it is used to generate the unique ID.
    If the serial number is missing, the physical device address is used
    (THIS IS LESS ACCURATE AND CHANGES IF DEVICE IS PLUGGED IN AT ANOTHER PORT).
    """

    vid = device.get('ID_VENDOR_ID', "VID_NOT_AVAILABLE")
    pid = device.get('ID_MODEL_ID', "PID_NOT_AVAILABLE")
    serial = device.get('ID_SERIAL_SHORT', None)
    dev_path = device.get('DEVPATH', "DEV_PATH_NOT_AVAILABLE")  # physical device path (e.g. /devices/pci0000:00/...)

    # 1. method: use serial number if present
    if serial is not None:
        unique_string = f"SERIAL:{serial}_VID:{vid}_PID:{pid}"
        print("[Info] USB device provides a serial number")
        print("[Info] Generating unique ID...")
    else:
        # 2. method (fallback): use device path
        unique_string = f"NOSERIAL_VID:{vid}_PID:{pid}_PATH:{dev_path}"
        print("[Info] USB device does NOT provide a serial number. Device path will be used to generate unique ID")
        print("[Info] Generating unique ID...")

    # hash with sha256
    device_hash = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
    print(f"[Info] Generated device hash: {device_hash}")
    return device_hash


def create_whitelist_file() -> bool:
    # Ensure the target directory exists
    if not os.path.exists(FILES_DIR):
        print(f"[Setup] Directory '{FILES_DIR}' does not exist. Creating it...")
        try:
            os.makedirs(FILES_DIR, exist_ok=True)
        except OSError as e:
            print(f"[Error] Could not create directory '{FILES_DIR}': {e}")
            return False

    # check if the target file exists
    if not os.path.exists(WHITELIST_FILEPATH):
        print(f"[Setup] Local file '{WHITELIST_FILEPATH}' not found. Creating it...")
        with open(WHITELIST_FILEPATH, "a") as f:
            pass

    return True


def is_device_whitelisted(device_hash: str) -> bool:
    create_whitelist_file()

    try:
        with open(WHITELIST_FILEPATH, 'r') as f:
            for line in f:
                if line.strip() == device_hash:
                    return True
        return False
    except IOError as e:
        print(f"[Error] Error while reading from the whitelist: {e}")
        return False


def add_to_whitelist_file(device_hash: str):
    if not device_hash:
        return False

    if is_device_whitelisted(device_hash):
        print(f"[Info] Device with hash {device_hash} is already present on whitelist")
        return False

    try:
        with open(WHITELIST_FILEPATH, 'a') as f:
            f.write(device_hash + '\n')
        print(f"[Info] Device with hash {device_hash} was added to the whitelist")
        return True
    except IOError as e:
        print(f"[Error] Error while writing to the whitelist: {e}")
        return False


# main function just for testing
if __name__ == "__main__":
    if download_usb_ids_conditionally():
        database = parse_usb_ids()
        print(f"[Info] Loaded {len(database)} vendors.")
