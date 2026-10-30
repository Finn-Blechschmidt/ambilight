#!/usr/bin/env python3
"""Samples a GPIO level register as fast as Python allows (no root, needs the gpio group).
Counts level changes on one pin to show whether something is actively driving it.
Usage: gpio_sample.py [pin=18] [seconds=1]"""
import mmap, os, struct, sys, time

pin = int(sys.argv[1]) if len(sys.argv) > 1 else 18
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
fd = os.open("/dev/gpiomem", os.O_RDONLY | os.O_SYNC)
mem = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ)
GPLEV0 = 0x34
unpack = struct.Struct("<I").unpack_from
mask = 1 << pin

n = hi = changes = 0
last = None
end = time.time() + secs
while time.time() < end:
    for _ in range(2000):
        v = unpack(mem, GPLEV0)[0] & mask
        n += 1
        if v:
            hi += 1
        if last is not None and v != last:
            changes += 1
        last = v
print(f"GPIO{pin}: {n} samples, high {100*hi/n:.1f}%, level changes {changes}")
