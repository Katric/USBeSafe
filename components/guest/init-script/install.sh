#!/bin/sh

# This scipt contains everything to make the vm be able to run the daemon and clam av virus script

# Install ClamAV packages
echo "[*] Installing ClamAV..."
apk add clamav clamav-daemon clamav-libunrar