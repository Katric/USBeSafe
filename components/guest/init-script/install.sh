#!/bin/sh
set -e

echo "[*] Base VM initialization started"

# --------------------------------------------------
# 1. Install ClamAV (scanner only; daemon optional)
# --------------------------------------------------
echo "[*] Installing ClamAV..."
apk update
apk add --no-cache clamav clamav-daemon clamav-libunrar

# Optional: do NOT enable clamd unless you really want it
# rc-update del clamd default || true

# --------------------------------------------------
# 2. Enable root autologin on tty1
# --------------------------------------------------
INITTAB="/etc/inittab"

echo "[*] Enabling root autologin on tty1..."

# Backup once
if [ ! -f /etc/inittab.bak ]; then
    cp "$INITTAB" /etc/inittab.bak
fi

# Replace getty with autologin shell
sed -i \
  's|^tty1::respawn:.*|tty1::respawn:/bin/ash --login|' \
  "$INITTAB"

# --------------------------------------------------
# 3. Apply changes
# --------------------------------------------------
echo "[*] Reloading init configuration..."
kill -HUP 1

echo "[✓] Initialization complete"
