# NucOffice – Projektnotizen & Plan

> Stand: 2026-11-23 · Status: **Kern + Installer (CLI) fertig, GUI folgt**

## 1. Ziel

NucOffice ist ein in Python geschriebener „Framework-Wrapper“ / Launcher für eine Sammlung
eigener Tools aus der Nuklearchemie. Es soll diese Tools einzeln oder gemeinsam

- **installieren** (von GitHub oder aus mitgelieferten Versionen, falls vorhanden),
- **aktualisieren**,
- **deinstallieren**,
- **starten**, **stoppen** und
- den **Laufstatus anzeigen**

können. Vor der Installation soll man den **Code ansehen** können.

Zielplattformen: **Windows** und **Linux** (macOS nicht primär, aber nichts verbauen).

## 2. Geplante Tools (5–9, vorerst 7)

Bestandsaufnahme der lokalen Projekte unter `~/Code/` (nur gelesen, 2026-11-20):

| Tool | GitHub | Lokaler Ordner | Paket / Startbefehl | Stand |
|---|---|---|---|---|
| plotSPE | `symbio-n0mad/plotSPE` (leer) | `~/Code/plotSPE/plotSPEKopie` | **keine `pyproject.toml`**, Start `python plotSPE.py`, `requirements.txt`; braucht **gnuplot** (System), optional TeX | Historie 529 Commits / 15 MB `.git` → Neuanfang |
| plotRDE | `symbio-n0mad/plotRDE` (leer) | `~/Code/radonEYE` | `radonlab` (hatchling), GUI `radonlab-gui`, Extras `[gui]`/`[all]`, Sphinx-Doku | ok |
| ActivityPartitioner | `symbio-n0mad/ActivityPartitioner` (leer) | `~/Code/activity-partitioning` | `activity-partitioning` 1.4.0, GUI `actpart-gui` | ok (kein git) |
| NucDB (Datenbank-Editor, früher „NC-database-editor“) | `symbio-n0mad/NucDB` (leer) | `~/Code/nc-database-editor` | Paket `nucdb` – erst Planung | Spezifikation `docs/NUCDB-SPEC.md` |
| HDTV | `hdtv-tool/hdtv` (fremd, Tags `v24.xx`) | – | `hdtv` (Konsole/IPython + ROOT-Fenster), GPL-2.0 | nur Linux, im Terminal starten |
| NC-Cyclovoltammetry | _noch kein Repo_ | – | – | Projekt existiert noch nicht, Repo folgt |
| NC-UV/VIS | _noch kein Repo_ | – | – | Projekt existiert noch nicht, Repo folgt |
| **NucOffice** | `symbio-n0mad/NucOffice` (leer) | `~/Code/NucOffice` | `nucoffice` | dieses Projekt |

SSH-Zugriff auf GitHub getestet: funktioniert (Konto `symbio-n0mad`), alle Repos leer.

Ist keine mitgelieferte Version vorhanden, ist nur die Installation von GitHub verfügbar.

## 2a. Arbeitsweise mit den Tool-Projekten

- Die Tool-Repos werden **aus ihren eigenen Projekten** heraus gepflegt und gepusht; hier wird
  nur NucOffice gepusht.
- Statt auf Pushes zu warten, liest NucOffice-Entwicklung die lokalen Projekte unter `~/Code/`
  **nur lesend**, um die Struktur zu kennen.
- Die Anforderungen von NucOffice an ein Tool stehen in **`docs/TOOL-SPEC.md`** (analog zu
  `NUCDB-SPEC.md`). Jedes Tool-Projekt kann diese Datei als Vorgabe einlesen (z. B. „bitte
  TOOL-SPEC aus NucOffice umsetzen“). So bleibt jede Änderung in ihrem eigenen Projekt.

**Festgelegt (2026-11-20):**
- Alle Tools sind in **Python** geschrieben, haben eine **GUI** und sind Pakete mit
  `pyproject.toml`. Fehlt eine `pyproject.toml`, wird sie im jeweiligen Tool-Repo ergänzt.
- Startbefehle ergeben sich aus den Entry-Points (`[project.gui-scripts]`/`[project.scripts]`)
  der `pyproject.toml` – werden beim Anlegen der Registry aus den Repos ausgelesen.
- **HDTV** = das bekannte HDTV (Python + ROOT). **Nur Linux**, Windows ist ausgeschlossen
  (wird in der Oberfläche unter Windows gar nicht angeboten).
- Alle Repos sind **öffentlich** → kein Token/SSH für Endnutzer nötig.
- NucOffice-Oberfläche: **PySide6 (Qt)**, ansprechend gestaltet.
- Updates: neueste Version von GitHub holen (Details s. Abschnitt „Updates“).

## 3. Anforderungen

### Installation
- Quelle wählbar: **GitHub** (Branch/Tag/Release, Commit wird gepinnt) oder **mitgeliefert**
  (Ordner `bundled/` mit Archiv + Prüfsumme).
- Einzeln oder mehrere/alle auf einmal.
- **Benutzer-Installation (Standard)**, ohne Admin-Rechte:
  - Linux: `~/.local/share/nucoffice/` (+ Starter in `~/.local/bin`, `.desktop`-Einträge)
  - Windows: `%LOCALAPPDATA%\NucOffice\` (+ Startmenü-Verknüpfungen)
- **Systemweite Installation** (mit Admin-Rechten):
  - Linux: `/opt/nucoffice/` (+ `/usr/local/bin`, `/usr/share/applications`), Rechte via `sudo`/`pkexec`
  - Windows: `%ProgramFiles%\NucOffice\` (+ öffentliches Startmenü), Rechte via UAC („runas“)
- Jedes Tool bekommt eine **eigene virtuelle Umgebung** (venv), damit sich Abhängigkeiten
  nicht beißen.

### Code-Ansicht vor Installation
- Quelle zuerst in einen **Staging-Ordner** herunterladen, nichts ausführen.
- Anzeigen: Dateibaum, Commit/Tag, Abhängigkeiten (`pyproject.toml`/`requirements.txt`),
  Dateien öffnen (im Editor/Dateimanager oder Link zur GitHub-Ansicht des gepinnten Commits).
- Bei **Updates**: Diff/Changelog zwischen installiertem und neuem Stand anzeigen.
- Erst nach Bestätigung wird installiert.

### Verwaltung
- **Update**: Bei Bedarf die neueste Version von GitHub holen. „Neueste Version“ =
  neuestes GitHub-Release/Tag, falls das Repo welche hat, sonst der aktuelle Stand von `main`.
  Vorher Diff zeigen, bei Fehler Rollback. Mitgelieferte Versionen dienen der
  Erst-/Offline-Installation; Updates kommen immer von GitHub.
- **Deinstallation**: Tool-Ordner, venv, Verknüpfungen und Status-Eintrag entfernen.
- **Start**: Tool als eigenen Prozess starten (losgelöst von NucOffice).
- **Stopp**: sauber beenden (terminate), nach Timeout erzwingen (kill).
- **Status**: läuft / läuft nicht / unbekannt, inkl. PID, Startzeit.
- **Dokumentation**: Pro Tool lässt sich die Doku aus NucOffice öffnen – **auch vor der
  Installation**, damit man vorab lesen kann, was das Tool kann.
  - Registry-Feld `docs` (z. B. `README.md` oder `docs/`-Ordner im Repo, oder eine Doku-URL).
  - Nicht installiert: Doku direkt von GitHub laden und in NucOffice anzeigen
    (Markdown-Ansicht in PySide6, Bilder inklusive), alternativ „Im Browser öffnen“.
  - Installiert bzw. mitgeliefert: lokale Kopie der Doku → funktioniert auch offline.

## 4. Technische Machbarkeit (Einschätzung)

| Funktion        | Machbar? | Anmerkung |
|-----------------|----------|-----------|
| Install/Update/Deinstall | ja | Python-Tools: problemlos. HDTV braucht ROOT (inkl. PyROOT) auf dem System – NucOffice prüft das und gibt sonst einen Hinweis; HDTV-venv mit Zugriff auf System-Pakete (`--system-site-packages`). Nur Linux. |
| Code ansehen    | ja | Staging-Download vor Installation. |
| Starten         | ja | `subprocess.Popen`, losgelöst (Linux: `start_new_session`, Windows: `DETACHED_PROCESS`/`CREATE_NEW_PROCESS_GROUP`). |
| Stoppen         | ja, mit Einschränkung | Zuverlässig für von NucOffice gestartete Prozesse. GUI-Tools beenden sich bei `terminate` evtl. ohne Speichern-Dialog. |
| Läuft es schon? | ja, mit Einschränkung | PID + Prozess-Startzeit in Statusdatei (gegen PID-Wiederverwendung) via `psutil`; zusätzlich Erkennung manuell gestarteter Instanzen über Kommandozeilen-Abgleich (heuristisch). Bei systemweiter Installation sieht ein Benutzer nur eigene Prozesse. |

## 5. Architektur (Entwurf)

```
nucoffice/
├── pyproject.toml
├── PLAN.md
├── tools.toml                # Registry: alle Tools, Repos, Startbefehle, Plattformen
├── bundled/                  # optionale mitgelieferte Versionen (+ SHA256)
├── src/nucoffice/
│   ├── registry.py           # liest tools.toml → Tool-Definitionen
│   ├── paths.py              # User-/System-Pfade je OS (platformdirs)
│   ├── sources/
│   │   ├── github.py         # Download (git clone ODER Zip über HTTPS, kein git nötig), Releases, Commits
│   │   └── bundled.py        # lokale Archive, Prüfsummen
│   ├── staging.py            # Download in Staging + Code-Ansicht/Diff
│   ├── installer.py          # venv anlegen, pip install, Verknüpfungen, Rollback
│   ├── elevation.py          # Admin-Rechte anfordern (sudo/pkexec bzw. UAC)
│   ├── shortcuts.py          # .desktop-Dateien / Windows-Startmenü
│   ├── process.py            # start/stop/status (psutil)
│   ├── state.py              # installed.json pro Scope (Version, Commit, Quelle, Pfad)
│   ├── cli.py                # Kommandozeile
│   └── gui/                  # grafische Oberfläche (Phase 2)
└── tests/
```

Beispiel Registry-Eintrag (`tools.toml`):

```toml
[tools.plotSPE]
display_name = "plotSPE"
repo = "https://github.com/<user>/plotSPE"
default_ref = "latest-release"     # oder "main" / fester Tag
install = "pip"                    # pip | script | custom
entry = "plotspe"                  # Startbefehl/Entry-Point
platforms = ["linux", "windows"]
bundled = "bundled/plotSPE-1.2.0.zip"   # optional
```

CLI-Skizze:

```
nucoffice list                     # alle Tools + Status (installiert/Version/läuft)
nucoffice show plotSPE             # Code in Staging laden und ansehen
nucoffice install plotSPE plotRDE [--source github|bundled] [--ref v1.2] [--system]
nucoffice install --all
nucoffice update [TOOL|--all]      # mit Diff-Vorschau
nucoffice uninstall TOOL
nucoffice start|stop|status TOOL
```

Abhängigkeiten (schlank halten): `platformdirs`, `psutil`, `PySide6`, stdlib `urllib`/`tomllib`
(Python ≥ 3.11). Die GUI ist die Hauptoberfläche; die CLI bleibt für Skripte/Tests und nutzt
denselben Kern.

## 6. Phasen

1. ✅ **Grundgerüst**: Projektstruktur, `pyproject.toml`, Registry, Pfade pro OS/Scope, Statusdatei.
2. 🟡 **Quellen & Staging**: ✅ GitHub-Download (Archiv, Commit-Pinning), ✅ Code-Ansicht
   (`nucoffice show`: Überblick, Abhängigkeiten, Startbefehle, Warnung bei setup.py/Build-Skripten,
   GitHub-Link und Vergleichslink zur installierten Version; `install` nimmt danach genau den
   angesehenen Stand) · offen: mitgelieferte Archive.
3. 🟡 **Installer**: ✅ venv pro Tool (eigener Ordner je Installation, da venvs nicht
   umbenennbar sind), Installation aus GitHub oder lokalem Ordner, Doku-Kopie, Deinstallation,
   Aufräumen bei Fehlern, ✅ Menüeinträge (Linux .desktop, Windows Startmenü – Windows ungetestet).
4. ✅ **Prozessverwaltung**: start/stop/status, Ausgabe des letzten Starts in einer Log-Datei;
   Konsolen-Tools (HDTV) im Terminal.
5. **Updates**: Versionsprüfung, Diff-Vorschau, Update mit Rollback.
6. **Systemweite Installation**: Rechteerhöhung Linux/Windows.
7. **GUI (PySide6)**: Kachel-/Listenansicht aller Tools mit Status (installiert, Version,
   läuft, Update verfügbar) und Aktionen (Installieren, Code ansehen, Update, Starten, Stoppen,
   Deinstallieren); Mehrfachauswahl; Fortschritt/Log; Hell/Dunkel-Modus.
8. **Verteilung von NucOffice selbst**: Zip (über GitHub Releases) + Selbst-Update.
9. **Tests & CI**: Unit-Tests, GitHub Actions auf Windows + Linux.

## 7. Offene Fragen

0. **HDTV-Version:** Das letzte HDTV-Release `v24.10` ist alt (noch `setup.py`), der Zweig
   `master` ist deutlich neuer (moderne `pyproject.toml`). Soll NucOffice für HDTV `master` statt
   des letzten Releases nehmen?

1. Repos für NC-Cyclovoltammetry und NC-UV/VIS – kommen, sobald die Projekte existieren.
2. ~~Anzeigenamen~~ geklärt: „plotRDE“ bleibt, der Datenbank-Editor heißt in NucOffice **„NucDB“**.
3. plotSPE braucht eine `pyproject.toml` mit GUI-Entry-Point (im plotSPE-Projekt umsetzen,
   Vorgabe: `docs/TOOL-SPEC.md`).

Bestehende Tool-Repos liegen **nur lokal** beim Nutzer (kein anderer Server). Volle
Historie dort sichern (z. B. `git bundle` als Backup), bevor der Neuanfang auf GitHub kommt.

Geklärt: Technologie (Python/GUI/pyproject), HDTV (bekanntes HDTV, nur Linux),
Repos öffentlich, GUI mit PySide6, Update-Quelle (neueste Version von GitHub),
Lizenz **GPL-3.0**, Verteilung als **Zip**, NucOffice liegt selbst auf GitHub und
**aktualisiert sich selbst**, Python wird vorausgesetzt (Installer liegt separat bei,
s. Abschnitt 11), Repo-Größe kommt von der **Historie** → sauberer Neuanfang auf GitHub
(Abschnitt 9), Doku pro Tool aus NucOffice öffnbar.

## 9. Repo-Größe & GitHub-Speicher

Grundsatz: **NucOffice kopiert die Tool-Repos nicht.** Die Registry (`tools.toml`) enthält
nur URLs; jedes Tool bleibt in seinem eigenen Repo. Keine Git-Submodule, keine Kopien.

- **Endnutzer laden keine Git-Historie**: NucOffice holt Release-Zips bzw. Quell-Archive
  eines Tags/Commits über HTTPS – nur den aktuellen Code-Stand, klein und ohne `git`.
- **Mitgelieferte Versionen** liegen nicht im NucOffice-Git, sondern im Verteil-Zip bzw.
  als Release-Asset.
- **Entscheidung:** Die Größe kommt von der Historie (plotSPE > 100 MB). Die volle Historie
  soll bewusst **nicht** auf GitHub. → Für jedes betroffene Tool wird auf GitHub nur ein
  **sauberer Neuanfang** veröffentlicht:
  1. Aktuellen Stand als einzelnen Start-Commit übernehmen (`git checkout --orphan` bzw.
     frisches Repo aus dem Arbeitsstand), vorher prüfen, dass keine großen/unnötigen
     Dateien im aktuellen Stand liegen (`.gitignore`).
  2. Auf GitHub pushen; ab dann läuft die weitere Entwicklung mit normaler Historie dort.
  3. Die alte, volle Historie bleibt lokal/am bisherigen Ort erhalten (optional als Archiv,
     z. B. `git bundle`), wird aber nicht hochgeladen.
- Allgemeine Optionen (zur Referenz):
  1. *Große Daten-/Binärdateien* (Spektren, Testdaten, Builds): aus dem Repo entfernen,
     per `.gitignore` ausschließen; Beispieldaten als Release-Asset oder z. B. auf Zenodo.
     Aus der Historie entfernen mit `git filter-repo`.
  2. *Lange Historie*: auf GitHub nur einen **sauberen Neuanfang** veröffentlichen
     (ein einzelner Start-Commit) – die volle Historie bleibt lokal/am bisherigen Ort erhalten.
  3. Kombination aus beidem.
- GitHub-Grenzen (Stand zu prüfen): normale öffentliche Repos haben kein festes Kontingent,
  aber Empfehlung < 1 GB, Einzeldatei max. 100 MB; begrenzt sind v. a. Git LFS, Packages
  und Actions-Speicher → **Git LFS vermeiden**.

## 10. Selbst-Update von NucOffice

- NucOffice prüft die neueste Release seines eigenen GitHub-Repos und lädt das Release-Zip.
- Ersetzen über einen kleinen Updater-Schritt: neues Zip in Nebenordner entpacken,
  NucOffice beenden, Ordner tauschen, neu starten (unter Windows sind laufende Dateien
  gesperrt, deshalb dieser Umweg). Alte Version bleibt für Rollback erhalten.
- Benutzerdaten/Einstellungen und installierte Tools liegen **außerhalb** des
  NucOffice-Programmordners und sind vom Update nicht betroffen.
- Lizenzdatei `LICENSE` (GPL-3.0) kommt beim Projektstart ins Repo.

## 12. Verteilung der Datenbank (NucDB)

Ziel: Endnutzer brauchen den Datenbank-Editor nicht – NucOffice liefert die Datenbank aus.
Abgestimmt mit `nc-database-editor/docs/NUCDB-SPEC.md` (Abschnitte 1.3 und 6).

- Datenbank = Ordner mit JSON-Dateien + `manifest.json` (`schema_version`, `data_version`,
  SHA-256 je Datei).
- **Offline-Momentaufnahme im NucOffice-Zip** (`bundled/nucdb/`). Beim ersten Start legt NucOffice
  sie in den gemeinsamen Datenordner:
  - Benutzer: Linux `~/.local/share/nucoffice/data/nucdb/`, Windows `%LOCALAPPDATA%\NucOffice\data\nucdb\`
  - systemweit: `/opt/nucoffice/data/nucdb/` bzw. `%ProgramFiles%\NucOffice\data\nucdb\`
  Die Tools finden sie dort ohne weitere Einstellung (Suchreihenfolge laut NUCDB-SPEC).
- **Updates**: NucOffice prüft die Releases des NucDB-Repos auf ein Daten-Asset
  (z. B. `nucdb-data-<data_version>.zip`), zeigt Versionsunterschied/Changelog, prüft
  Prüfsummen und `schema_version` (gleiche MAJOR-Version), tauscht den Ordner atomar aus
  und behält die vorige Version für Rollback.
- Lokale Änderungen der Nutzer werden nicht überschrieben, ohne zu fragen
  (Prüfsummen weichen vom Manifest ab → Nachfrage).
- Offen: Format/Name des Release-Assets mit dem NucDB-Projekt festlegen.

## 11. Python-Voraussetzung

- NucOffice setzt ein **installiertes Python (≥ 3.11)** voraus; es wird **nicht** in
  NucOffice eingebettet.
- Windows: Das Verteil-Zip enthält zusätzlich den **offiziellen Python-Installer von
  python.org als separate Datei** (z. B. `python-installer/python-3.x.y-amd64.exe`), den man
  bei Bedarf **manuell** ausführt – alternativ selbst herunterladen.
  Hinweis in der Anleitung: „Add python.exe to PATH“ anhaken.
- Linux: Python aus der Distribution (meist vorhanden); kein Installer im Zip, nur Hinweis.
- Startskripte im Zip (`NucOffice.bat` / `nucoffice.sh`) prüfen, ob passendes Python
  vorhanden ist; falls nicht, verständliche Meldung mit Verweis auf den beiliegenden
  Installer bzw. python.org. Beim ersten Start legt NucOffice sich eine eigene venv an
  und installiert PySide6 & Co. dort hinein.

## 8. Infrastruktur

- SSH-Schlüssel (ed25519, ohne Passphrase) erzeugt: `~/.ssh/id_ed25519` / `~/.ssh/id_ed25519.pub`,
  Kommentar `claude-code@nucoffice`. Öffentlichen Schlüssel auf GitHub hinterlegen.
