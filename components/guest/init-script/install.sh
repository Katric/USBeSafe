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
# 2. Enable root autologin on tty1 AND ttyS0
# --------------------------------------------------
INITTAB="/etc/inittab"

echo "[*] Enabling root autologin on tty1 and ttyS0..."

# Backup once
if [ ! -f /etc/inittab.bak ]; then
    cp "$INITTAB" /etc/inittab.bak
fi

# Autologin for GUI/VNC console
sed -i \
  's|^tty1::respawn:.*|tty1::respawn:/bin/ash --login|' \
  "$INITTAB"

# Autologin for serial / -nographic console
if grep -q '^ttyS0::respawn:' "$INITTAB"; then
    sed -i \
      's|^ttyS0::respawn:.*|ttyS0::respawn:/bin/ash --login|' \
      "$INITTAB"
else
    echo 'ttyS0::respawn:/bin/ash --login' >> "$INITTAB"
fi

# --------------------------------------------------
# 3. Apply changes
# --------------------------------------------------
echo "[*] Reloading init configuration..."
kill -HUP 1

echo "[✓] Initialization complete"
