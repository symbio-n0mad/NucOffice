# NucOffice

Installiert, aktualisiert, startet und stoppt die NC-Tools für die Nuklearchemie
(plotSPE, plotRDE, ActivityPartitioner, NucDB, HDTV, …) unter Windows und Linux.

Status: in Entwicklung. Plan: [PLAN.md](PLAN.md) · Anforderungen an Tools: [docs/TOOL-SPEC.md](docs/TOOL-SPEC.md)

## Starten (Entwicklung)

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[gui,dev]'
.venv/bin/nucoffice-gui          # Oberfläche
.venv/bin/nucoffice --help       # Kommandozeile
```

Die Oberfläche zeigt alle Tools mit Status (installiert, Version, läuft, Update verfügbar) und
bietet: Installieren, Aktualisieren, Code vor der Installation ansehen, Dokumentation lesen
(auch vor der Installation), Starten/Beenden, Deinstallieren, Mehrfachauswahl, Hell/Dunkel.

Lizenz: GPL-3.0-or-later
