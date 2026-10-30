# Hardware und Systemänderungen am Pi

## Grabber (verifiziert, 2026-10-30)
- `lsusb`: `05e1:0408` Syntek STK1160, Kernel-Treiber `stk1160`, Device `/dev/video0`, am USB-Hub `usb-3f980000.usb-1.1.3`.
- Eingänge: Composite0..3, S-Video. Genutzt wird Composite0 (Eingang 0).
- Nur Pixelformat UYVY. Default nach dem Laden: NTSC-M 720x480, deshalb PAL setzen.

## Systemänderungen am Pi
Bisher keine. Vorhanden: `rsync`, `python3`, `v4l2-ctl`. Nicht vorhanden: `git`, `ffmpeg`.

## Stromversorgung des Pi (Problem, 2026-10-30)
- Beobachtung: Während M1 verlor der Pi (WLAN) die Verbindung und tauchte erst nach Neustart per LAN unter neuer IP wieder auf. Die Ursache vom WLAN-Abbruch selbst ist nicht belegt.
- Messung nach dem Neustart: `vcgencmd get_throttled` = `0xf0005`. Bedeutung: Unterspannung **aktuell aktiv** (Bit 0), aktuell gedrosselt (Bit 2), und seit dem Boot aufgetreten: Unterspannung, Frequenzbegrenzung, Throttling, Temperaturlimit (Bits 16-19).
- Einordnung: Das Netzteil oder Kabel des Pi liefert unter Last (Grabber am USB-Hub, Ethernet) zu wenig Spannung. Das kann den WLAN-Ausfall erklären, ist aber nur eine Vermutung. Das Journal ist nicht persistent, ein Log des Ausfalls existiert nicht.
- Konsequenz: Vor Benchmarks (M6) und vor dem ersten Ansteuern der LEDs (M2) muss `get_throttled` auf `0x0` stehen, sonst sind CPU- und Latenzmessungen wertlos.
