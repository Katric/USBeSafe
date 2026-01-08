#!/usr/bin/env bash

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
fi

ROOT="/opt/usbesafe"
DAEMON_BIN="host/usbesafed/target/debug/usbesafed"
CLI_BIN="host/usbesafe-cli/target/debug/usbesafe-cli"
GUI_SRC="host/usbesafe-gui"

# `usbesafe` user for CLI and GUI
if ! id -u usbesafe >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin usbesafe
fi

mkdir -p "$ROOT" "$ROOT/run"

# install binaries
install -m 755 "$DAEMON_BIN" "$ROOT"
cp "shared/virtio-schema.json" "$ROOT"
chown root:usbesafe "$ROOT/virtio-schema.json"
chmod 440 "$ROOT/virtio-schema.json"
install -m 755 -o usbesafe -g usbesafe "$CLI_BIN" "$ROOT"

# install GUI
cp -r "$GUI_SRC" "$ROOT"
chown -R usbesafe:usbesafe "$ROOT/usbesafe-gui"

# symlinks
ln -sf "$ROOT/usbesafe-cli" /usr/local/bin/usbesafe-cli
ln -sf "$ROOT/usbesafe-gui/main.py" /usr/local/bin/usbesafe-gui

# for unix socket at /opt/usbesafe/run/usbesafed.sock
chown -R root:usbesafe "$ROOT/run"
chmod -R 770 "$ROOT/run"

# systemd unit for daemon
cat <<EOF > "/etc/systemd/system/usbesafed.service"
[Unit]
Description=usbesafed
After=network.target

[Service]
Type=simple
ExecStart=$ROOT/usbesafed
Restart=always
RestartSec=5
User=root
WorkingDirectory=$ROOT

[Install]
WantedBy=multi-user.target
EOF

# restart daemon
systemctl daemon-reload
systemctl enable usbesafed
systemctl restart usbesafed
