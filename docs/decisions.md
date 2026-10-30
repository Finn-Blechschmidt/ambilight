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
