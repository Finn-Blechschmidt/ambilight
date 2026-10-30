#!/usr/bin/env python3
"""Safe LED test patterns for the WS2812B strip (run on the Pi with sudo, inside the venv).

Safety limits (not configurable on the command line):
  - global brightness <= MAX_BRIGHTNESS
  - at most MAX_LIT LEDs lit at once
  - all LEDs are switched off on exit, on Ctrl-C and on SIGTERM

Colors are sent as raw R,G,B bytes in wire order "RGB". The color you see tells the real order:
  sent red   -> you see red   : first byte is R
  sent red   -> you see green : strip is GRB (common for WS2812B)

Usage:
  led_test.py off
  led_test.py color [--index 0] [--brightness 10]    # red, green, blue one after another
  led_test.py walk  [--start 0] [--stop 20]          # one LED moves, prints the index
  led_test.py mark  --index 17                        # one white LED
"""
import argparse, signal, sys, time

from rpi_ws281x import PixelStrip, Color, WS2811_STRIP_RGB

LED_COUNT = 109
LED_PIN = 18
MAX_BRIGHTNESS = 32
MAX_LIT = 8


def make_strip(brightness):
    brightness = max(0, min(int(brightness), MAX_BRIGHTNESS))
    # args: count, pin, freq, dma channel, invert, brightness, pwm channel, strip type
    strip = PixelStrip(LED_COUNT, LED_PIN, 800000, 10, False, brightness, 0, WS2811_STRIP_RGB)
    strip.begin()
    return strip


def clear(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def set_leds(strip, leds):
    if len(leds) > MAX_LIT:
        raise SystemExit(f"refusing to light {len(leds)} LEDs (limit {MAX_LIT})")
    clear(strip)
    for idx, (r, g, b) in leds.items():
        strip.setPixelColor(idx, Color(r, g, b))
    strip.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["off", "color", "walk", "mark"])
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=20)
    p.add_argument("--brightness", type=int, default=10)
    p.add_argument("--delay", type=float, default=1.0)
    a = p.parse_args()

    strip = make_strip(a.brightness)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: sys.exit(0))
    try:
        if a.mode == "off":
            clear(strip)
        elif a.mode == "color":
            for name, rgb in (("red", (255, 0, 0)), ("green", (0, 255, 0)), ("blue", (0, 0, 255))):
                print(f"sending {name} on LED {a.index}", flush=True)
                set_leds(strip, {a.index: rgb})
                time.sleep(a.delay * 2)
        elif a.mode == "walk":
            for i in range(a.start, min(a.stop, LED_COUNT)):
                print(f"LED {i}", flush=True)
                set_leds(strip, {i: (255, 255, 255)})
                time.sleep(a.delay)
        elif a.mode == "mark":
            set_leds(strip, {a.index: (255, 255, 255)})
            print(f"LED {a.index} on, Ctrl-C to stop", flush=True)
            while True:
                time.sleep(1)
    finally:
        clear(strip)


if __name__ == "__main__":
    main()
