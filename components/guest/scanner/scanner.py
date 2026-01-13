#!/usr/bin/env python3
import subprocess
import logging
import sys
import os

# ---------------- CONFIG ----------------
LOG_FILE = "/var/log/clamav-wrapper.log"
FRESHCLAM_CONFIG = "/etc/clamav/freshclam.conf"

# ---------------- LOGGING (must be set up BEFORE logger is used) ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("clamav-wrapper")

# ---------------- ARGUMENT CHECKS ----------------
if len(sys.argv) != 2:
    logger.error("Usage: %s <scan_directory>", sys.argv[0])
    sys.exit(2)

SCAN_DIR = sys.argv[1]

if not os.path.isdir(SCAN_DIR):
    logger.error("Scan directory does not exist or is not a directory: %s", SCAN_DIR)
    sys.exit(2)


def run_freshclam():
    logger.info("Starting ClamAV database update (freshclam)")

    process = subprocess.Popen(
        [
            "freshclam",
            "--config-file",
            FRESHCLAM_CONFIG,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        logger.info("[freshclam] %s", line.rstrip())

    process.wait()

    if process.returncode == 0:
        logger.info("ClamAV database update completed successfully")
    else:
        logger.warning(
            "freshclam exited with code %s — continuing with scan",
            process.returncode,
        )


def run_scan():
    logger.info("Starting ClamAV scan on directory: %s", SCAN_DIR)

    process = subprocess.Popen(
        [
            "clamscan",
            "-r",
            "-v",
            SCAN_DIR,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    infected = False

    for line in process.stdout:
        line = line.rstrip()
        logger.info("[clamav] %s", line)

        if "FOUND" in line:
            infected = True

    process.wait()

    if process.returncode == 1:
        logger.warning("Malware detected")
        return True
    elif process.returncode == 0:
        logger.info("Scan completed successfully — no malware found")
        return False
    else:
        logger.error("ClamAV exited with error code %s", process.returncode)
        sys.exit(2)


if __name__ == "__main__":
    logger.info("Script started")

    run_freshclam()
    infected = run_scan()

    # Exit codes expected by the VM daemon:
    # 0 = clean, 1 = infected, 2 = scanner error
    sys.exit(1 if infected else 0)

