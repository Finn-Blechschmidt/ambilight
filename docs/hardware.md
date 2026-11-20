# Hardware, wiring and system changes

Status of this document: last hands-on session was 2026-10-30. Everything below is what was measured then;
nothing here claims a working LED output.

## Components

| Component | Details |
|---|---|
| Computer | Raspberry Pi 3 Model B+ Rev 1.3 (4x Cortex-A53, 1 GB RAM), Raspberry Pi OS Lite 64-bit (Debian, kernel `6.18.50+rpt-rpi-v8`) |
| Source splitter | Portta HDMI splitter 1x2 (N2SP12MD) |
| Converter | HDMI-to-AV converter (composite out) with a PAL/NTSC switch, own power supply. **The switch must be on NTSC** ([ADR-004](decisions.md#adr-004-ntsc-instead-of-pal-on-converter-and-grabber-supersedes-adr-002)) |
| Grabber | CSL USB video grabber, Syntek STK1160 (`05e1:0408`), decoder `saa7113`, driver `stk1160`, device `/dev/video0` |
| LEDs | WS2812B-type strip, 5 V, three wires (+5 V, data, GND), 5050 LEDs with one capacitor each, 109 LEDs in use (type inferred from the pad markings, not from a data sheet) |
| LED supply | S-50-5 enclosed switching supply: 5 V / 10 A (50 W), adjustable output voltage (potentiometer) |

### Signal chain

```
Source -> HDMI splitter -> output 1: TV
                        -> output 2: HDMI-to-AV converter -> composite (yellow RCA) -> USB grabber -> Pi
```

The analogue composite link is the hard upper limit for resolution, picture quality and frame rate.

## Grabber (verified 2026-10-30)

- `lsusb`: `05e1:0408` Syntek STK1160, driver `stk1160`, `/dev/video0`.
- Inputs: Composite0 to Composite3 and S-Video. Composite0 to 3 give the same picture (one physical composite
  input); S-Video gives black. Input 0 is used.
- Only pixel format: UYVY. After loading the driver the default is NTSC-M 720x480.
- Working configuration: input 0, standard `ntsc-m`, 720x480, UYVY, interlaced, about 29.97 frames/s.
- Colour only arrives with the converter switch **and** the grabber standard on NTSC. In PAL the picture is black
  and white (chroma exactly 0).
- With no HDMI signal the converter outputs a grey 8-bar "NO SIGNAL" test pattern (observed in PAL mode).

## LED strip layout and power budget

Layout, from the owner's sketch. The strip starts at the bottom centre, right next to a gap of one LED:

```
                    top: 35
        +-------------------------------+
        |                               |
 left   |                               |  right
  20    |                               |   20
        |                               |
        +------17-------[ ]-------17----+
                         ^ gap of 1 LED
                         ^ strip start (LED 0) right of the gap
```

Total: 17 + 17 + 20 + 20 + 35 = **109 LEDs**. The direction of travel (clockwise or not) and the colour order are
**not verified yet** (M2).

| Quantity | Value |
|---|---|
| LEDs | 109 |
| Current per LED at full white (WS2812B) | about 60 mA (3 x 20 mA) |
| Maximum current, all LEDs full white | 109 x 60 mA = 6.5 A |
| Supply S-50-5 | 5 V / 10 A |
| Reserve at full white (without the Pi) | 3.5 A |

Consequences:
- The supply can carry the maximum, but 6.5 A through a long strip causes a voltage drop (white turns yellowish).
  The pipeline will limit the total current from a value in the config (not implemented yet). The test tool has hard
  limits ([ADR-006](decisions.md#adr-006-hard-safety-limits-in-the-led-test-tool)).
- First test load: 1 LED at brightness 10 of 255 draws about 2.4 mA at white. The other 108 LEDs get black (idle
  current about 1 mA each, roughly 0.1 A in total).
- A WS2812B at 5 V expects at least 0.7 x VDD = 3.5 V at its data input. The Pi outputs 3.3 V. This often works
  with short wires, but it is a well-known risk. A 74AHCT125 / 74HCT245 level shifter is the standard fix.
- Common ground between the Pi and the strip supply is required (Pi GND pin 6 to the strip GND).

### Wiring as reported by the owner

| Pi header | Wire | Strip side |
|---|---|---|
| Pin 12 = GPIO 18 (PWM0) | yellow | green wire of the 3-pin JST connector (data) |
| Pin 6 = GND | black | white wire (GND) |
| (separate) | barrel plug | 5 V power from the S-50-5 |

The assignment of the JST colours (red +5 V, green data, white GND) is a common convention and was not measured.

## Power supply of the Pi: investigation log

Symptom: the Pi reported under-voltage from the first boot on. Observed once: it dropped off Wi-Fi during M1 and
came back only after a power cycle, on Ethernet.

`vcgencmd get_throttled` bits: 0 under-voltage now, 1 ARM frequency capped now, 2 throttled now, 3 soft temperature
limit now; 16 to 19 are the same conditions "has occurred since boot". A healthy system reads `0x0`.

| # | Setup | `get_throttled` | Temperature | Notes |
|---|---|---|---|---|
| 1 | Pi on the LED supply S-50-5, converter powered from the Pi | `0xf0005`, later `0xf0007` | 82.2 C | under-voltage and frequency cap active |
| 2 | external supply, Pi free in the air | `0xf0007` | 82.2 C | `dmesg`: "Undervoltage detected" at 18 s, ARM clock 600 MHz |
| 3 | phone charger rated 5 V / 2 A, converter on its own supply | `0xd0005` | 66.6 C | frequency cap gone, under-voltage stays; the temperature changed, so the sensor was not stuck (the earlier heat was probably the converter and the supply next to the Pi, not verified) |
| 4 | same charger, different cable (Voltcraft DO-10) | `0x50005` | 75.2 C | unchanged |
| 5 | same, grabber unplugged | `0x50005` | 77.4 C | stable for over 10 minutes: the grabber is not the cause |

Conclusion so far: under-voltage persists at idle, without USB load, with two cables and two supplies. The cause is
**not resolved**. Suspects: high resistance in the Pi's input path (micro-USB connector, polyfuse), or a defective
board (it is visibly bent). The owner ordered a replacement Pi 3 B+. Until then, CPU and timing measurements from
this Pi are not valid ([ADR-003](decisions.md#adr-003-keep-developing-on-the-faulty-pi-move-measurements-to-the-replacement-pi)).
Not tried: measuring the voltage at test points TP1/TP2 with a multimeter, feeding 5 V directly into the GPIO header.

Safety observation from a photo: at one point the Pi lay directly on the metal housing of the open S-50-5 whose mains
terminals are covered only by a transparent cap. Keep the Pi and loose data wires away from the mains side.

## LED bring-up log (M2, not finished)

1. **Software side.** `tools/led_test.py` runs without errors (single LED red/green/blue, five LEDs white at
   brightness 32). Afterwards `pinctrl get 18` shows `a5 = PWM0`.
2. **Signal on the pin.** With `led_test.py mark --stream` running, the pin level register was sampled without
   root. Idle: 0 level changes. Streaming: 15,000 to 27,000 level changes per second, 8 to 12 % high. A C sampler
   (`tools/gpio_pulse.c`, 111 ns per read, 4 million reads) found 111,265 high pulses: width peak 400 to 499 ns,
   rising-edge spacing peak 1200 to 1299 ns. That is correct WS2812B timing at 800 kHz. The voltage amplitude at
   the strip is not known.
3. **Strip reaction.** No LED lit. Variants tried: 800 kHz and 400 kHz, 24 bit and 32 bit (RGBW), five LEDs white
   at brightness 32. Photo of the strip: 5050 LEDs with one capacitor each, pads `+5V / DO / GND` and
   `+5V / Din / GND`, an arrow in the data direction. Three wires, so not an APA102/WS2801 type.
4. **Pin read-back.** With nothing but the wiring changed (the owner swapped the data and ground wires between pin
   6 and pin 12 as an experiment), the pins were driven high and low and read back:

   | Pin | Result |
   |---|---|
   | GPIO 12 | follows correctly |
   | GPIO 18 | reads high always, also as a floating input (earlier the same day it followed correctly) |
   | GPIO 21 (pin 40, not wired) | reads low always, even when driven high |

   Either something holds GPIO 18 high externally, or the pin is damaged. The pull-up/pull-down check with
   `pinctrl` is not usable on the BCM2837 (unconnected pins read low as well).
5. **Open next steps:** measure the pins with the header wires removed to separate wiring from pin damage; try a
   different data pin (GPIO 12 on pin 32 with GND on pin 34, or GPIO 21 on pin 40 with GND on pin 39); measure
   the data voltage at the strip with a multimeter; try a level shifter; try another strip; repeat on the replacement Pi.

## System changes on the Pi

Applied by `deploy/setup.sh` (needs `sudo`, run by hand because the password cannot be automated):

| Change | Why |
|---|---|
| `apt install rsync python3 python3-venv python3-dev scons gcc v4l-utils` | deployment, capture tools, building `rpi_ws281x` |
| `/boot/firmware/config.txt`: `dtparam=audio=on` -> `dtparam=audio=off`, reboot | analogue audio uses the PWM block that drives GPIO 18 |
| persistent systemd journal (`/var/log/journal`) | keep a log after a crash |
| Python virtual environment `~/ambilight/.venv` with `rpi_ws281x` | LED output |

Already present on a fresh Pi OS Lite image: `rsync`, `python3`, `v4l2-ctl`. Not present: `git`, `ffmpeg`.
After disabling audio the card list shows only HDMI and the grabber's audio; the empty kernel module
`snd_bcm2835` stays loaded and does not interfere.
