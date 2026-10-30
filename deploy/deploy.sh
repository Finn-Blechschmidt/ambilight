#!/usr/bin/env bash
# Synchronises the project to the Raspberry Pi with one command.
# Usage: deploy/deploy.sh [--dry-run]
# The target is an SSH host alias (default "ambilight") from ~/.ssh/config,
# so no IP address or user name lives in the repository.
set -euo pipefail

HOST="${AMBILIGHT_HOST:-ambilight}"
REMOTE_DIR="${AMBILIGHT_REMOTE_DIR:-ambilight}"   # relative to the remote home
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RSYNC_OPTS=(-az --delete --human-readable --stats
  --exclude '.git/' --exclude '.DS_Store' --exclude '__pycache__/'
  --exclude '*.local.*' --exclude 'captures/' --exclude 'CLAUDE.md')
[[ "${1:-}" == "--dry-run" ]] && RSYNC_OPTS+=(--dry-run)

ssh -o BatchMode=yes -o ConnectTimeout=8 "$HOST" "mkdir -p '$REMOTE_DIR'"
rsync "${RSYNC_OPTS[@]}" "$ROOT/" "$HOST:$REMOTE_DIR/"
echo "Deployed to $HOST:~/$REMOTE_DIR"
