#!/usr/bin/env bash
# Prepares a fresh Raspberry Pi OS Lite for the project (idempotent). Run ON the Pi as the normal user;
# it asks for the sudo password. Every system change made here is also listed in docs/hardware.md.
set -euo pipefail
APP_DIR="$HOME/ambilight"

sudo apt-get update
sudo apt-get install -y rsync python3 python3-venv python3-dev scons gcc v4l-utils

# GPIO 18 drives the LEDs through the PWM block. Analog audio (snd_bcm2835) uses the same
# block, so it must be off. A reboot is required for this to take effect.
CFG=/boot/firmware/config.txt
if grep -q '^dtparam=audio=on' "$CFG"; then
  sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' "$CFG"
  echo "Analog audio switched off in $CFG -> reboot required."
fi

# Keep the journal across reboots so a crash leaves a log behind.
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install rpi_ws281x

echo "Throttle state (expect 0x0):"
vcgencmd get_throttled
