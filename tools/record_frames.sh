#!/usr/bin/env bash
# Records raw UYVY frames on the Pi and copies them to the Mac (for replays, benchmarks and test material).
# Usage: tools/record_frames.sh [frames] [out_file]    default: 300 frames (10 s) -> captures/frames.uyvy
# The frames are as delivered by the grabber: 720x480 NTSC, so the converter switch must be on NTSC (ADR-004).
set -euo pipefail

HOST="${AMBILIGHT_HOST:-ambilight}"
DEV="${AMBILIGHT_VIDEO_DEV:-/dev/video0}"
INPUT="${AMBILIGHT_INPUT:-0}"
STD="${AMBILIGHT_STD:-ntsc-m}"
W="${AMBILIGHT_W:-720}"; H="${AMBILIGHT_H:-480}"
N="${1:-300}"
OUT="${2:-captures/frames.uyvy}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$(dirname "$ROOT/$OUT")"

ssh -o BatchMode=yes "$HOST" "
  v4l2-ctl -d $DEV -i $INPUT -s $STD >/dev/null &&
  v4l2-ctl -d $DEV --set-fmt-video=width=$W,height=$H,pixelformat=UYVY >/dev/null &&
  v4l2-ctl -d $DEV --stream-mmap=4 --stream-skip=15 --stream-count=$N --stream-to=/tmp/frames.uyvy >/dev/null 2>&1 &&
  ls -l /tmp/frames.uyvy | awk '{print \$5, \"bytes\"}'"
scp -q "$HOST:/tmp/frames.uyvy" "$ROOT/$OUT"
echo "Saved $OUT ($(( $(stat -f%z "$ROOT/$OUT" 2>/dev/null || stat -c%s "$ROOT/$OUT") / (W * H * 2) )) frames)"
