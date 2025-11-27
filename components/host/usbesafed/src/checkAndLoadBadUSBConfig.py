import sys
from pathlib import Path

CONFIG_DIR = "/etc/usbesafe/"
CONFIG_NAME = "usbesafe.conf"

BAD_USB_PROTECTION = "BAD_USB_PROTECTION"


def get_config_file():
    """Returns the path to the usbesafe configuration file"""

    config_dir = Path(CONFIG_DIR)
    config_file = config_dir / CONFIG_NAME

    if not config_file.is_file():
        print(f"ERROR: The configuration file '{config_file}' is missing")
        sys.exit(1)

    return config_file


def load_usbesafe_config():
    """Reads the 'usbesafe.conf' config file from the '/etc/usbesafe/' directory and returns a dictionary"""

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
        print("ERROR: No permissions to read the file contents (forgot sudo?)")
        sys.exit(1)

    # check if necessary attributes are present in the config file
    required_keys = [BAD_USB_PROTECTION]
    missing_keys = [key for key in required_keys if key not in config_values]

    if missing_keys:
        print(f"ERROR: The following keys are missing from the config file: {', '.join(missing_keys)}")
        sys.exit(1)

    try:
        config_values[BAD_USB_PROTECTION] = int(config_values[BAD_USB_PROTECTION])
    except ValueError:
        print("ERROR: The values of the config file needs to be numbers (e.g. 0 oder 1).")
        sys.exit(1)

    print("Config successfully read")

    for key, value in config_values.items():
        print(f"{key} is set to {value}")

    return config_values


if __name__ == "__main__":
    load_usbesafe_config()
