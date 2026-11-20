#!/usr/bin/env bash
# Installs and starts the systemd service. Run ON the Pi as the normal user; it asks for the sudo password.
# It creates config/ambilight.local.toml from the example if there is none (the local file is never deployed).
set -euo pipefail
APP_DIR="$HOME/ambilight"
LOCAL="$APP_DIR/config/ambilight.local.toml"

[[ -f "$LOCAL" ]] || { cp "$APP_DIR/config/ambilight.example.toml" "$LOCAL"; echo "Created $LOCAL"; }

sed "s|@HOME@|$HOME|g" "$APP_DIR/deploy/ambilight.service.in" | sudo tee /etc/systemd/system/ambilight.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now ambilight.service
systemctl --no-pager status ambilight.service | head -8
echo "Logs: journalctl -u ambilight -f"
