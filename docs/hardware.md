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

### Test ohne Grabber (2026-10-30)
- Grabber im Betrieb abgezogen (`lsusb` zeigt kein 05e1), Pi lief weiter (Uptime 8 bis 10 min). Über 3 Minuten unverändert: `get_throttled` = `0x50005` (Unterspannung und Throttling aktuell aktiv), 77,4 °C, nur 1 Unterspannungsmeldung in `dmesg` seit dem Boot.
- Ergebnis: Der Grabber ist nicht die Ursache. Der Pi sieht im Leerlauf ohne USB-Last dauerhaft zu wenig Eingangsspannung, mit zwei Kabeln und zwei Versorgungen. Verdacht: hoher Widerstand im Eingangspfad des Pi (Micro-USB-Buchse, Sicherung/Polyfuse) oder Netzteile, die unter 4,63 V liegen.
- Nächster Test: 5 V direkt am GPIO-Header einspeisen (umgeht Buchse und Sicherung).

## LED-Streifen: Layout und Stromrechnung (2026-10-30)
Angaben von Finn (Skizze): Start unten in der Mitte rechts neben einer Lücke von einer LED. Unten links 17 und unten rechts 17 LEDs, rechts 20, oben 35, links 20. Gesamt **109 LEDs** (17+17+20+20+35). Datenleitung an GPIO 18 (Pin 12), Masse an Pin 6. Laufrichtung (rechts oder links herum) und Farbreihenfolge sind noch nicht verifiziert (M2).

| Größe | Wert |
|---|---|
| LEDs | 109 |
| Strom pro LED bei Vollweiß (WS2812B) | ca. 60 mA (3 x 20 mA) |
| Maximalstrom aller LEDs | 109 x 60 mA = 6,5 A |
| Netzteil S-50-5 | 5 V / 10 A (50 W) |
| Reserve bei Vollweiß | 3,5 A, ohne Pi |

Folgerungen:
- Das Netzteil trägt den Maximalstrom, aber 6,5 A über einen langen Streifen führt zu Spannungsabfall (Weißanteil wird gelblich). Die Software begrenzt die Summe auf einen Strom, der in der Config steht (Standard für die Tests: sehr niedrig).
- Teststrom: 1 LED mit Helligkeit 10 von 255 zieht rund 60 mA x 10/255 = 2,4 mA bei Weiß, bei einer Farbe weniger. Die übrigen 108 LEDs bekommen Schwarz (Ruhestrom je LED ca. 1 mA, rund 0,1 A insgesamt).
- Der Pi hängt aktuell an einem eigenen Ladegerät, die Masse ist über Pin 6 mit dem Streifen verbunden (gemeinsame Masse nötig).
- WS2812B erwartet am Dateneingang mindestens 0,7 x VDD = 3,5 V. Der Pi liefert 3,3 V. Das funktioniert oft mit kurzer Leitung, ist aber ein bekanntes Risiko und wird im Test beobachtet (Flackern, falsche Farben, erste LED reagiert nicht).

## Systemänderungen am Pi (Stand LED-Vorbereitung)
`deploy/setup.sh` führt aus (mit sudo, per Hand von Finn):
- Pakete: `rsync python3 python3-venv python3-dev scons gcc v4l-utils`.
- `/boot/firmware/config.txt`: `dtparam=audio=on` -> `dtparam=audio=off` (analoges Audio belegt den PWM-Block für GPIO 18). Neustart nötig.
- Persistentes systemd-Journal (`/var/log/journal`), damit nach einem Absturz ein Log bleibt.
- Python-venv `~/ambilight/.venv` mit `rpi_ws281x`.

### Erster LED-Test (2026-10-30): keine LED leuchtet
- Software: `tools/led_test.py color` (LED 0, Helligkeit 10) und `mark --count 5` (Helligkeit 32) laufen ohne Fehler. Nach dem Lauf steht GPIO 18 laut `pinctrl get 18` auf `a5` = `PWM0`. Die Ausgabe am Pi ist also konfiguriert. Ob am Pin tatsächlich ein Signal anliegt und ankommt, ist damit nicht belegt.
- Offen (nur physisch prüfbar): Welcher Header-Pin trägt das gelbe Kabel (Foto nicht eindeutig), Anschlussbelegung des 3-adrigen JST-Steckers am Streifen (rot/grün/weiß, vermutlich rot +5 V, grün Daten, weiß GND, ungeprüft), Spannung am Streifen, gemeinsame Masse.
- Beobachtungen auf den Fotos: S-50-5 läuft (grüne LED an), Netzklemmen sind mit einer durchsichtigen Kappe abgedeckt, ein graues Kabel liegt quer über der Abdeckung. Die Pfeile auf dem Streifen zeigen vom Anschlussende weg (Hinweis, dass der Stecker am Dateneingang sitzt, nicht bestätigt).

### Signalmessung am GPIO 18 (2026-10-30)
Verkabelung laut Finn: gelbes Kabel Pin 12 (GPIO 18) auf grüne Ader am Streifen (Daten), schwarzes Kabel Pin 6 (GND) auf weiße Ader (Masse). Das Netzteil und die Streifen-LEDs funktionierten früher mit anderer Ansteuerung.
- Methode: `led_test.py mark --stream` sendet alle 10 ms ein Bild. Dazu liest `tools/gpio_sample.py` (Python) und `tools/gpio_pulse.c` (C, 111 ns pro Lesevorgang) das GPIO-Level-Register ohne Root.
- Ruhezustand: 0 Pegelwechsel, 0,0 % high.
- Mit Stream: 15 000 bis 27 000 Pegelwechsel pro Sekunde, 8 bis 12 % high.
- Pulsbreiten (4 Mio. Lesevorgänge, 111 265 High-Pulse): 300 bis 599 ns, Schwerpunkt 400 bis 499 ns. Flanke zu Flanke: 1100 bis 1399 ns, Schwerpunkt 1200 bis 1299 ns. Das entspricht dem WS2812B-Timing (800 kHz, Null-Bit ca. 0,4 µs high, Periode 1,25 µs).
- Ergebnis: Der Pi erzeugt das richtige Signal am Pin. Der Fehler liegt dahinter: Pegel (3,3 V statt der geforderten mind. 3,5 V bei 5 V Versorgung), Kontakt, gemeinsame Masse oder der Dateneingang des Streifens. Die Amplitude kann mit dieser Messung nicht beurteilt werden.

### Streifentyp und Pegeltest (2026-10-30)
- Foto der Pads: 5050-LEDs mit Kondensator `C1` je LED, Pads `+5V / DO / GND` und `+5V / Din / GND`, Pfeil zeigt Richtung Datenfluss. Drei Adern, also kein APA102. Passt zur WS2812B-Familie, 5 V sicher laut Finn.
- Die vier Varianten `led_test.py mark --stream` (800/400 kHz, 24/32 Bit) liefen am Streifen ohne sichtbare Reaktion.
- `pinctrl`-Test (ohne Root): GPIO 18 als Ausgang auf High gesetzt liest `hi`, auf Low gesetzt `lo`. Der Pin ist also nicht hart gegen Masse oder 5 V kurzgeschlossen. Die Pull-up/Pull-down-Messung ist unbrauchbar (auch unbelegte Pins 24 und 25 lesen `lo`, `pinctrl` setzt die Pulls auf dem BCM2837 offenbar nicht).
- Offen: Amplitude am Streifenende, Durchgang der Datenader, Zustand des ersten LED-Chips.

### GPIO-Pegeltest nach Umstecken (2026-10-30)
Finn hat gelbes (Daten) und schwarzes (Masse) Kabel zwischen Pin 6 und Pin 12 getauscht (keine LED leuchtete). Danach `pinctrl`-Test, je Pin als Ausgang High/Low gesetzt und zurückgelesen:
- GPIO 12: folgt korrekt (hi/lo), Pin ist in Ordnung.
- GPIO 18: liest immer `hi`, auch bei Low und als freier Eingang. Vorher am selben Tag folgte er korrekt. Der Pin wird extern auf High gehalten oder ist beschädigt.
- GPIO 21 (Pin 40, unbelegt): liest immer `lo`, auch bei High. Verdacht: Ausgang defekt oder gegen Masse gebrückt.
- Konsequenz: Zuerst Header ohne Kabel messen, um äußere Verdrahtung von Pin-Schaden zu trennen. `led_test.py` hat jetzt `--pin` (12, 13, 18, 19, 21).
