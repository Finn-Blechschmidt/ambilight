#!/usr/bin/env bash
# Prepares a fresh Raspberry Pi OS Lite for the project (idempotent). Run ON the Pi.
# Every system change made here is also listed in docs/hardware.md.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y rsync python3 v4l-utils

# Make the power state visible in logs after a crash (journal is volatile by default).
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald

echo "Throttle state (expect 0x0):"
vcgencmd get_throttled
