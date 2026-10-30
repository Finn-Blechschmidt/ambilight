#!/usr/bin/env python3
"""Convert a raw UYVY frame (BT.601, limited range) to PNG without dependencies.
Usage: uyvy2png.py in.uyvy out.png [width height]"""
import struct, sys, zlib

def clamp(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)

def main():
    src, dst = sys.argv[1], sys.argv[2]
    w, h = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (720, 576)
    raw = open(src, "rb").read()
    rows = []
    for y in range(h):
        line = raw[y * w * 2:(y + 1) * w * 2]
        out = bytearray(b"\x00")
        for i in range(0, w * 2, 4):
            u, y0, v, y1 = line[i:i + 4]
            for yy in (y0, y1):
                c, d, e = 1.164 * (yy - 16), u - 128, v - 128
                out += bytes((clamp(c + 1.596 * e), clamp(c - 0.392 * d - 0.813 * e), clamp(c + 2.017 * d)))
        rows.append(bytes(out))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")
    open(dst, "wb").write(png)

main()
