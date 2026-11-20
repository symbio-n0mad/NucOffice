# NucOffice – Anforderungen an ein Tool (TOOL-SPEC)

**Version: 0.1 (ENTWURF)** · Stand 2026-11-20 · gepflegt im Projekt NucOffice

Dieses Dokument richtet sich an die **Tool-Projekte** (plotSPE, plotRDE/radonlab,
ActivityPartitioner, NucDB, …). Es beschreibt, was ein Tool erfüllen muss, damit NucOffice es
installieren, aktualisieren, starten/stoppen und seine Doku anzeigen kann. Jedes Projekt kann
diese Datei direkt als Umsetzungsvorgabe einlesen.

## 1. Paket

1. Python-Paket mit **`pyproject.toml`** im Wurzelverzeichnis des Repos (PEP 621,
   beliebiges Build-Backend: setuptools, hatchling …). `pip install .` muss funktionieren.
2. `requires-python` gesetzt; NucOffice setzt Python ≥ 3.11 voraus.
3. Die GUI-Abhängigkeiten müssen bei `pip install .` oder über ein Extra installierbar sein.
   NucOffice installiert das Extra, das in der NucOffice-Registry eingetragen ist (z. B. `[gui]`).
4. Version in `[project] version` (oder dynamisch aus Git-Tags). Releases als Git-Tag `vX.Y.Z`
   (empfohlen: zusätzlich ein GitHub-Release).

## 2. Startbefehl

1. Die GUI wird über einen Eintrag in **`[project.gui-scripts]`** gestartet, z. B.
   ```toml
   [project.gui-scripts]
   plotspe = "plotspe.app:main"
   ```
   (`gui-scripts` statt `scripts`, damit unter Windows kein Konsolenfenster erscheint.)
2. Die Funktion muss **ohne Argumente** ein Fenster öffnen. Dateipfade als Argumente sind optional.
3. Beenden: Das Tool soll auf `SIGTERM` (Linux) bzw. das normale Schließen des Prozesses
   (Windows) ohne Hängenbleiben reagieren. Ungespeicherte Arbeit sollte das Tool idealerweise
   selbst sichern (Autosave), da NucOffice „Stoppen“ anbietet.

## 3. Daten und Einstellungen

1. **Nicht** in den Installationsordner schreiben (der kann schreibgeschützt sein, z. B. bei
   systemweiter Installation). Einstellungen/Sitzungen in den Benutzerordner
   (`platformdirs.user_config_dir("<tool>")` o. Ä.).
2. Messdaten, große Dateien und Build-Ergebnisse gehören nicht ins Repo (`.gitignore`).
3. Die gemeinsame Nukliddatenbank wird nach `NUCDB-SPEC.md` gefunden (NucOffice-Datenordner).

## 4. Dokumentation

1. Eine **`README.md`** im Repo-Wurzelverzeichnis, die beschreibt, was das Tool kann
   (NucOffice zeigt sie **vor der Installation** an). Bilder mit relativen Pfaden sind erlaubt.
2. Optional ausführlichere Doku unter `docs/`; der Einstiegspunkt wird in der NucOffice-Registry
   eingetragen (z. B. `docs/index.md` oder eine URL).

## 5. Externe Abhängigkeiten

Nicht über pip installierbare Voraussetzungen (z. B. `gnuplot`, TeX, ROOT) in der README und in
der NucOffice-Registry (`requires_system`) nennen. NucOffice prüft sie vor der Installation und
gibt einen Hinweis.

## 6. Repo

1. Öffentliches GitHub-Repo unter `symbio-n0mad/`.
2. Keine große Historie hochladen (Neuanfang mit einem Start-Commit, siehe NucOffice-PLAN).

## Versionshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-11-20 | Erster Entwurf |
