import subprocess
import logging
import sys
import os

SCAN_DIR = "/your/directory" #TODO: add scan dir

LOG_FILE = "/var/log/clamav-wrapper.log"
FRESHCLAM_CONFIG = "/etc/clamav/freshclam.conf"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("clamav-wrapper")


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
    result = run_scan()

    print("true" if result else "false")

