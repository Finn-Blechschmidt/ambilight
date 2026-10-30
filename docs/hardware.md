# Hardware und Systemänderungen am Pi

## Grabber (verifiziert, 2026-10-30)
- `lsusb`: `05e1:0408` Syntek STK1160, Kernel-Treiber `stk1160`, Device `/dev/video0`, am USB-Hub `usb-3f980000.usb-1.1.3`.
- Eingänge: Composite0..3, S-Video. Genutzt wird Composite0 (Eingang 0).
- Nur Pixelformat UYVY. Default nach dem Laden: NTSC-M 720x480, deshalb PAL setzen.

## Systemänderungen am Pi
Bisher keine. Vorhanden: `rsync`, `python3`, `v4l2-ctl`. Nicht vorhanden: `git`, `ffmpeg`.
