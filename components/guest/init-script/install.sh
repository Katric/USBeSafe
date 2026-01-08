#!/bin/sh
set -e

echo "[*] Base VM initialization started"

# --------------------------------------------------
# 1. Install ClamAV (scanner only; daemon optional)
# --------------------------------------------------
echo "[*] Installing ClamAV..."

# Enable Alpine community repository (v3.22) to be able to install clamav
APK_REPO_FILE="/etc/apk/repositories"
COMMUNITY_REPO="http://dl-cdn.alpinelinux.org/alpine/v3.22/community"

if grep -qE "^\s*#\s*${COMMUNITY_REPO}$" "$APK_REPO_FILE"; then
    sed -i "s|^\s*#\s*${COMMUNITY_REPO}$|${COMMUNITY_REPO}|" "$APK_REPO_FILE"
fi

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
