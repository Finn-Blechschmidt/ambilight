# Ambilight

Eigenbau-Ambilight auf einem Raspberry Pi 3B+: Das TV-Bild wird per USB-Grabber abgegriffen, Randfarben werden berechnet und in Echtzeit auf einen WS2812B-LED-Streifen ausgegeben.

> Status: Aufbau läuft (M0). Foto/GIF folgt.

## Deploy
```bash
deploy/deploy.sh
```
Voraussetzung: SSH-Alias `ambilight` in `~/.ssh/config` (Key-Login).

Weitere Abschnitte (Hardware, Architektur, Kennzahlen, Entstehung) folgen mit den Meilensteinen. Entscheidungen: [docs/decisions.md](docs/decisions.md).
