# Entscheidungslog (ADR)

Jeder Eintrag: Datum, Kontext, Optionen, Entscheidung, Begründung, Messung, Konsequenzen.
Revidierte Entscheidungen werden nicht gelöscht, sondern verlinkt.

## ADR-001: Deploy per rsync über SSH-Host-Alias
- Datum: 2026-10-30
- Kontext: Entwicklung auf dem Mac, Ausführung auf dem Pi. Das Repo wird öffentlich, darf also keine IPs oder Benutzernamen enthalten. Deploy soll mit einem Befehl funktionieren.
- Betrachtete Optionen:
  1. `rsync` vom Mac auf den Pi. Vorteil: schnell, kein Git-Zugang auf dem Pi nötig, auch uncommittete Änderungen testbar. Nachteil: Pi-Stand ist nicht automatisch an einen Commit gebunden.
  2. `git pull` auf dem Pi. Vorteil: Stand ist ein Commit. Nachteil: braucht Remote und Commit/Push pro Testlauf, Iteration langsamer.
  3. CI/Paketbau (z. B. .deb). Vorteil: sauber. Nachteil: für den Umfang überdimensioniert.
- Entscheidung: Option 1, `deploy/deploy.sh`, Ziel über SSH-Alias `ambilight` (überschreibbar per `AMBILIGHT_HOST`).
- Begründung: kürzeste Iterationszeit auf dem Pi; Host-Details bleiben in `~/.ssh/config` und damit außerhalb des Repos.
- Messung/Beleg: Deploy-Test steht noch aus, der Pi war bei M0-Start nicht erreichbar (No route to host).
- Konsequenzen/Trade-offs: `--delete` entfernt Dateien auf dem Pi, die lokal fehlen. Der Zielordner `~/ambilight` darf daher keine Handarbeit enthalten.

## ADR-002: Capture-Grundeinstellungen (Eingang, Norm, Format)
- Datum: 2026-10-30
- Kontext: Der STK1160 (`/dev/video0`, Treiber `stk1160`) startet mit NTSC-M, 720x480. Die Signalkette ist PAL (625 Zeilen, 25 Hz, interlaced).
- Betrachtete Optionen:
  1. Norm automatisch erkennen lassen (`PAL|NTSC`). Vorteil: kein Eingriff nötig. Nachteil: Der Treiber startet in NTSC, Erkennung wurde nicht geprüft und kann bei Signalverlust springen.
  2. Norm fest auf PAL setzen (aus Config). Vorteil: deterministisch, 720x576 sofort. Nachteil: nicht für NTSC-Quellen, für diesen Aufbau irrelevant.
- Entscheidung (vorläufig, M1): Eingang 0 (Composite0), Norm PAL (`v4l2-ctl -s pal`), Format UYVY 720x576, Feld Interlaced. Der Treiber bietet nur UYVY an.
- Begründung: Mit diesen Werten kam beim ersten Versuch ein stabiles Bild. Die Werte kommen später aus der Config.
- Messung/Beleg: Ein Frame (829440 Bytes = 720*576*2) aufgenommen, per `tools/uyvy2png.py` konvertiert. Zu sehen ist das Konverter-Testbild „NO SIGNAL“, die Signalquelle war aus. Der Grabber synchronisiert also sauber auf den Konverter.
- Erkenntnis: Der HDMI-to-AV-Konverter gibt ohne HDMI-Signal ein graues 8-Balken-Bild mit Text „NO SIGNAL“ aus. Die Signalüberwachung (M5) muss dieses Muster erkennen (Graustufen, keine Farbe), sonst zeigen die LEDs Müll.
- Noch offen: Bild mit echter Quelle prüfen, Interlacing-Verhalten und Overscan-Ränder beurteilen, Frame-Timing messen. Die Aufnahme zeigte schwarze Ränder links und unten. `VIDIOC_CREATE_BUFS` meldet einen harmlosen Fehler von v4l2-ctl.
- Konsequenzen/Trade-offs: PAL ist fest verdrahtet, solange die Config nichts anderes sagt.

### Nachtrag ADR-002 (2026-10-30): Bild mit echter Quelle
- Mit laufender Quelle: stabiles Bild, gemessen 25,00 fps (100 Frames, `v4l2-ctl --stream-count=100`), 720x576.
- Ränder: ca. 8 Pixel schwarz links/rechts/oben/unten (Luma ~26-35 statt ~215 im Bild). Das ist Overscan/Austastung und wird später beim Zuschnitt entfernt.
- **Problem: Das Bild ist komplett schwarzweiß.** U und V sind in allen Pixeln exakt 128 (Chroma 0,0). Das gilt für PAL-BG, PAL-N, PAL-Nc, SECAM, PAL-60, NTSC-443 und den Default. Die Decoder-Farbverstärkung steht per AGC auf 15 (Default 40), der Decoder sieht also keinen Farbträger.
- Einordnung: Die Normumschaltung ändert nichts. Wahrscheinlich liefert die Kette (Konverter oder Quelle) kein Farbsignal. Treiberseitig gibt es keinen Hinweis auf einen Fehler. Ohne Farbe wäre das Ambilight nutzlos, das Problem blockiert M1.

## ADR-003: Entwicklung auf dem defekten Pi fortsetzen, Messungen auf den Ersatz-Pi verschieben
- Datum: 2026-10-30
- Kontext: Der Pi meldet dauerhaft Unterspannung (`get_throttled=0x50005`), auch ohne Grabber, mit zwei Kabeln und zwei Netzteilen. Die Platine ist sichtbar verbogen, Finn vermutet einen Hardwaredefekt und bestellt einen Ersatz-Pi 3B+.
- Betrachtete Optionen:
  1. Stoppen, bis der neue Pi da ist. Vorteil: keine Messung auf kaputter Hardware. Nachteil: Stillstand, obwohl der Großteil der Arbeit hardwareunabhängig ist.
  2. Weiterentwickeln auf dem alten Pi, Messungen und LED-Tests später auf dem neuen. Vorteil: Fortschritt. Nachteil: Ergebnisse vom alten Pi sind nur eingeschränkt gültig.
  3. Image vom alten Pi auf den neuen klonen. Vorteil: schnell. Nachteil: übernimmt Altlasten und ist nicht reproduzierbar dokumentiert.
- Entscheidung: Option 2, und der neue Pi wird per `deploy/setup.sh` eingerichtet statt per Image-Klon.
- Begründung: Capture, Pipeline-Logik, Farbmathematik, Glättung und Tests laufen hardwareunabhängig. Das Setup-Skript erfüllt die Pflicht, ein frisches Image reproduzierbar einzurichten (Arbeitsregel 4).
- Was auf dem alten Pi NICHT belastbar ist: CPU-Last, Latenz, FPS unter Last, Temperatur, jede Zeitmessung (Takt ist durch Unterspannung begrenzt, im Leerlauf 600 MHz). Die Sprachwahl (ADR) wird deshalb erst nach Messungen auf dem neuen Pi festgelegt, bis dahin entsteht nur sprachunabhängiger Code und Doku.
- LEDs: Der erste LED-Test (M2) findet nur auf dem neuen Pi statt. Der Streifen ist zeitkritisch (Takt), und eine verbogene, unterversorgte Platine ist ein unnötiges Risiko für Pi und LEDs.
- Konsequenzen/Trade-offs: Ein Teil der Meilensteine (M3 bis M6) schiebt sich nach hinten. Messwerte von heute werden in `benchmarks.md` als „alter Pi, ungültig“ markiert.
