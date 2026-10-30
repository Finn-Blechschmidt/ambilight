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
