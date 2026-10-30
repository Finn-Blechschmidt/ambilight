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

### Nachmessung (2026-10-30, nach Neustart, feste IP <pi-address> per Fritzbox-DHCP-Reservierung)
- Versorgung: Der Pi hängt am LED-Netzteil S-50-5 (5 V / 10 A), nicht an einem eigenen Pi-Netzteil. Das Netzteil selbst ist ausreichend dimensioniert, die Unterspannung entsteht also eher auf dem Weg zum Pi (Kabel, Klemmen, Einstellung der Ausgangsspannung) als durch fehlende Leistung.
- `get_throttled` = `0xf0007`: Unterspannung und Frequenzbegrenzung aktiv, 1 Minute nach dem Boot. Kerntemperatur 82 °C kurz nach dem Boot (ohne nennenswerte Last), das ist auffällig hoch.
- Offen: Spannung am Pi (Testpunkte TP1/TP2 der 3B+) mit Multimeter messen, Ausgangsspannung des Netzteils am Poti prüfen, Kabelquerschnitt und -länge klären.

### Test mit externem Netzteil (2026-10-30)
- Pi an einem externen Netzteil, frei in der Luft. Nach 2 Minuten Uptime weiterhin `get_throttled` = `0xf0007`, `dmesg`: `Undervoltage detected!` bei 18 s, ARM-Takt 600 MHz (begrenzt). Die Kerntemperatur zeigt unverändert 82,2 °C wie in der Messung davor. Ein identischer Wert nach zwei Neustarts ist verdächtig, der Sensor ist damit nicht als verlässlich zu betrachten.
- Die Unterspannung liegt also nicht (nur) am LED-Netzteil. Ursache offen: externes Netzteil/Kabel, USB-Last oder die Messung selbst.
- Foto-Beobachtung: Der Pi lag direkt auf dem Gehäuse des offenen S-50-5, dessen Netzanschlussklemmen unabgedeckt waren (Sicherheitsrisiko). Ein gelbes Datenkabel hing frei in der Nähe der Klemmen. Der Aufbau wird vor M2 sauber getrennt.

### Test mit OnePlus-Ladegerät, Konverter eigenes Netzteil (2026-10-30)
- Netzteil: OnePlus Warp Charge 30, Modell WC0506A3HK, Ausgang 5 V / 2 A (6 A nur mit Warp-Protokoll und Spezialkabel). Der HDMI-AV-Konverter war vorher über USB am Pi angeschlossen und hängt jetzt an einem eigenen Netzteil. Der Grabber blieb am Pi.
- Ergebnis: `get_throttled` = `0xd0005`, Unterspannung weiterhin aktiv (`dmesg`: bei 19 s und 71 s). Die Frequenzbegrenzung (Bit 1) ist nicht mehr aktiv. Kerntemperatur 66,6 °C statt 82,2 °C, der Sensor war also nicht eingefroren, der Pi war vorher durch Konverter und Netzteilnähe wärmer.
- Folgerung: Die Last allein erklärt es nicht, Kabel oder Ladegerät liefern am Pi weniger als ca. 4,63 V (Schwelle der Unterspannungsmeldung). Nächster Test: anderes Kabel, anderes Netzteil.

### Test mit Voltcraft-DO-10-Kabel am OnePlus-Ladegerät (2026-10-30)
- Pi startete normal, per LAN unter <pi-address> erreichbar. Nach 2 Minuten: `get_throttled` = `0x50005`, 1 Unterspannungsmeldung in `dmesg`, 75,2 °C im Leerlauf.
- Unterspannung bleibt aktiv, das Kabel ist nicht (allein) die Ursache. Nächster Test: anderes Netzteil.
