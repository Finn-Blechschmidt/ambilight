#!/usr/bin/env bash
# Captures one raw UYVY frame on the Pi and converts it to PNG on the Mac.
# Usage: tools/capture_frame.sh [out.png]   (default: captures/frame.png)
set -euo pipefail

HOST="${AMBILIGHT_HOST:-ambilight}"
DEV="${AMBILIGHT_VIDEO_DEV:-/dev/video0}"
INPUT="${AMBILIGHT_INPUT:-0}"
STD="${AMBILIGHT_STD:-ntsc-m}"
W="${AMBILIGHT_W:-720}"; H="${AMBILIGHT_H:-480}"
OUT="${1:-captures/frame.png}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$(dirname "$ROOT/$OUT")"

ssh -o BatchMode=yes "$HOST" "
  v4l2-ctl -d $DEV -i $INPUT -s $STD >/dev/null &&
  v4l2-ctl -d $DEV --set-fmt-video=width=$W,height=$H,pixelformat=UYVY >/dev/null &&
  v4l2-ctl -d $DEV --stream-mmap=4 --stream-skip=15 --stream-count=1 --stream-to=/tmp/capture.uyvy >/dev/null 2>&1"
scp -q "$HOST:/tmp/capture.uyvy" "$TMP/f.uyvy"
python3 "$ROOT/tools/uyvy2png.py" "$TMP/f.uyvy" "$ROOT/$OUT" "$W" "$H"
python3 - "$TMP/f.uyvy" <<'PY'
import sys
d = open(sys.argv[1], "rb").read()
u, v, y = d[0::4], d[2::4], d[1::2]
print(f"luma mean {sum(y)/len(y):.0f}, chroma |U-128| {sum(abs(x-128) for x in u)/len(u):.2f}, |V-128| {sum(abs(x-128) for x in v)/len(v):.2f}")
PY
echo "Saved $OUT"
