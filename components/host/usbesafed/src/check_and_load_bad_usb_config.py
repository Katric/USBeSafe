import os
import sys

BAD_USB_PROTECTION = "BAD_USB_PROTECTION"

# --- Configuration & Path Setup ---

# determine the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# calculate the path to the 'files' directory
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../"))
FILES_DIR = os.path.join(PROJECT_ROOT, "files")
# define the full path to the usbesafe.conf file
BAD_USB_PROTECTION_CONFIG_FILEPATH = os.path.join(FILES_DIR, "usbesafe.conf")


def get_config_file():
    """
    Ensures the directory and the configuration file exist.
    Returns the path to the config file if successful, otherwise False.
    """

    # Ensure the target directory exists
    if not os.path.exists(FILES_DIR):
        print(f"[Setup] Directory '{FILES_DIR}' does not exist. Creating it...")
        try:
            os.makedirs(FILES_DIR, exist_ok=True)
        except OSError as e:
            print(f"[Error] Could not create directory '{FILES_DIR}': {e}")
            return False

    # Ensure the config file exists with default content
    if not os.path.exists(BAD_USB_PROTECTION_CONFIG_FILEPATH):
        print(f"[Setup] Config file '{BAD_USB_PROTECTION_CONFIG_FILEPATH}' missing. Creating default...")
        try:
            with open(BAD_USB_PROTECTION_CONFIG_FILEPATH, "w") as f:
                #############################################################
                # --> just add all config in this line, followed by an \n <--
                #############################################################
                f.write("BAD_USB_PROTECTION = 0\n")
        except OSError as e:
            print(f"[Error] Could not create config file: {e}")
            return False

    return BAD_USB_PROTECTION_CONFIG_FILEPATH


def load_usbesafe_config():
    """
    Reads the 'usbesafe.conf' config file from the '/files/' directory and returns a dictionary with keys and values
    """

    config_file = get_config_file()

    config_values = {}

    # read config file line by line
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # ignore comments and empty lines
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    config_values[key.strip()] = value.strip()

    except PermissionError:
        print("[Error] No permissions to read the file contents (forgot sudo?)")
        sys.exit(1)

    # check if necessary attributes are present in the config file
    required_keys = [BAD_USB_PROTECTION]
    missing_keys = [key for key in required_keys if key not in config_values]

    if missing_keys:
        print(f"[Error] The following keys are missing from the config file: {', '.join(missing_keys)}")
        sys.exit(1)

    try:
        config_values[BAD_USB_PROTECTION] = int(config_values[BAD_USB_PROTECTION])
    except ValueError:
        print("[Error] The values of the config file needs to be numbers (e.g. 0 oder 1).")
        sys.exit(1)

    print("usbesafe.conf successfully read")

    for key, value in config_values.items():
        print(f"{key} is set to {value} ({bool(value)})")

    return config_values


def set_bad_usb_protection_status(status_value):
    """
    Updates ONLY the BAD_USB_PROTECTION value in the config file,
    preserving other lines.

    Args:
        status_value (int): 0 to disable, 1 to enable.
    """
    config_path = get_config_file()
    if not config_path:
        return False

    if status_value not in [0, 1]:
        print(f"[Error] Invalid status value: {status_value}")
        return False

    try:
        with open(config_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        found = False
        target_key = "BAD_USB_PROTECTION"

        # search and update line (modify)
        for line in lines:
            if line.strip().startswith(target_key):
                new_lines.append(f"{target_key} = {status_value}\n")
                found = True
            else:
                new_lines.append(line)

        # if key does not exist yet, it will be appended
        if not found:
            new_lines.append(f"{target_key} = {status_value}\n")

        # write back all lines into the file
        with open(config_path, "w") as f:
            f.writelines(new_lines)

        print(f"[Config] Updated protection status to: {status_value}")
        return True

    except OSError as e:
        print(f"[Error] Could not update config file: {e}")
        return False


if __name__ == "__main__":
    load_usbesafe_config()
