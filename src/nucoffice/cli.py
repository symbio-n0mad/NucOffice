"""Kommandozeile von NucOffice (die Oberfläche in nucoffice.gui nutzt denselben Kern)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, actions, installer, process, staging
from .paths import Scope, layout
from .registry import load_registry
from .sources import bundled
from .state import State


def _cmd_list(args) -> int:
    reg = load_registry()
    state = State(layout(args.scope).state_file)
    for key, tool in reg.items():
        inst = state.get(key)
        version = inst.version if inst else "–"
        running = "läuft" if process.status(key) else ""
        note = "" if tool.supported else "(auf diesem System nicht verfügbar)"
        if tool.supported and bundled.available(key):
            note = "mitgeliefert: " + (bundled.available(key).version or bundled.available(key).ref)
        print(f"{key:22} {tool.display_name:22} {version:12} {running:6} {note}")
    return 0


def _cmd_status(args) -> int:
    info = process.status(args.tool)
    print(f"{args.tool}: läuft (PID {info.pid})" if info else f"{args.tool}: läuft nicht")
    return 0


def _cmd_stop(args) -> int:
    print("beendet" if process.stop(args.tool) else "läuft nicht")
    return 0


def _get_tool(key: str):
    reg = load_registry()
    if key not in reg:
        raise SystemExit(f"Unbekanntes Tool '{key}'. Verfügbar: {', '.join(reg)}")
    return reg[key]


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _cmd_show(args) -> int:
    """Code laden (nicht ausführen) und Überblick zeigen."""
    tool, lay = _get_tool(args.tool), layout(args.scope)
    try:
        staged = actions.obtain(tool, lay, args.source, args.ref, reuse_staged=False)
    except (OSError, bundled.BundleError) as exc:
        print(f"Fehler beim Laden: {exc}", file=sys.stderr)
        return 1
    s = staging.summarize(staged.path)
    origin = "mitgeliefert" if staged.source == "bundled" else "GitHub"
    print(f"{tool.display_name} – Stand {staged.ref} ({actions.short(staged.commit)}, Quelle: {origin})")
    print(f"  Code geladen nach: {staged.path}")
    if staged.browse_url:
        print(f"  Auf GitHub ansehen: {staged.browse_url}")
    inst = State(lay.state_file).get(tool.key)
    if inst and inst.commit and staged.commit and inst.commit != staged.commit:
        print(f"  Änderungen seit installierter Version {inst.version}: {staged.compare_url(inst.commit)}")
    elif inst and staged.commit and inst.commit == staged.commit:
        print(f"  Dieser Stand ist bereits installiert ({inst.version}).")
    print(f"  Paket: {s.name or '(aus setup.py)'} {s.version or '(Version dynamisch)'}, "
          f"Python {s.requires_python or '?'}")
    print(f"  Dateien: {s.file_count} ({s.python_files} Python), {_fmt_size(s.size_bytes)}")
    print("  Abhängigkeiten: " + (", ".join(s.dependencies) or "keine"))
    for extra in tool.extras:
        print(f"  Zusatz [{extra}]: " + ", ".join(s.optional.get(extra, [])))
    print("  Startbefehle: " + (", ".join(s.entry_points) or "keine"))
    if s.build_hooks:
        print("  Achtung, führt beim Installieren Code aus: " + ", ".join(s.build_hooks))
    print(f"Installieren dieses Stands: nucoffice install {tool.key}")
    if args.open:
        staging.open_folder(staged.path)
    return 0


def _cmd_install(args) -> int:
    tool, lay = _get_tool(args.tool), layout(args.scope)
    try:
        if args.source_path:
            installer.install(tool, Path(args.source_path), lay, source="local", ref="local")
            return 0
        staged = actions.obtain(tool, lay, args.source, args.ref, reuse_staged=True)
        try:
            installer.install(tool, staged.path, lay, source=staged.source,
                              ref=staged.ref, commit=staged.commit)
        finally:
            staging.discard(tool, lay)
    except (installer.InstallError, bundled.BundleError, OSError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_bundle(args) -> int:
    """Mitgelieferte Version aus einem lokalen Projekt packen (für das Release-Zip)."""
    tool = _get_tool(args.tool)
    try:
        entry = bundled.create(tool.key, Path(args.source_dir), version=args.version, ref=args.ref)
    except (OSError, bundled.BundleError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    print(f"{tool.display_name} {entry.version or entry.ref} gepackt: "
          f"{bundled.bundled_dir() / entry.file} ({actions.short(entry.commit)})")
    if entry.commit is None:
        print("  Hinweis: kein Git-Repo – Ordner wurde ohne venv/build/Cache-Ordner gepackt.")
    return 0


def _cmd_uninstall(args) -> int:
    tool = _get_tool(args.tool)
    try:
        if not installer.uninstall(tool, layout(args.scope)):
            print(f"{tool.display_name} ist nicht installiert.")
    except installer.InstallError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_start(args) -> int:
    tool = _get_tool(args.tool)
    try:
        info = process.start(tool.key, installer.launch_command(tool, layout(args.scope)))
    except (installer.InstallError, RuntimeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    print(f"{tool.display_name} gestartet (PID {info.pid})")
    return 0


def _cmd_gui(args) -> int:
    from .gui.app import main as gui_main
    return gui_main()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nucoffice", description="NC-Tools verwalten")
    p.add_argument("--version", action="version", version=f"NucOffice {__version__}")
    p.add_argument("--system", dest="scope", action="store_const", const=Scope.SYSTEM,
                   default=Scope.USER, help="systemweite Installation verwenden")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="alle Tools mit Status").set_defaults(func=_cmd_list)
    sub.add_parser("gui", help="grafische Oberfläche öffnen").set_defaults(func=_cmd_gui)
    sp = sub.add_parser("install", help="Tool installieren oder aktualisieren (neueste Version)")
    sp.add_argument("tool")
    sp.add_argument("--from", dest="source_path", metavar="ORDNER",
                    help="aus lokalem Quellordner statt von GitHub installieren")
    sp.add_argument("--ref", help="bestimmte Version (Tag/Branch/Commit) statt der neuesten")
    sp.add_argument("--source", choices=["auto", "github", "bundled"], default="auto",
                    help="Quelle: GitHub, mitgelieferte Version oder auto (GitHub, offline mitgeliefert)")
    sp.set_defaults(func=_cmd_install)
    sp = sub.add_parser("show", help="Code vor der Installation laden und ansehen")
    sp.add_argument("tool")
    sp.add_argument("--ref", help="bestimmte Version (Tag/Branch/Commit) statt der neuesten")
    sp.add_argument("--open", action="store_true", help="Ordner im Dateimanager öffnen")
    sp.add_argument("--source", choices=["auto", "github", "bundled"], default="auto",
                    help="Quelle: GitHub, mitgelieferte Version oder auto (GitHub, offline mitgeliefert)")
    sp.set_defaults(func=_cmd_show)
    sp = sub.add_parser("bundle", help="(Entwicklung) mitgelieferte Version aus lokalem Projekt packen")
    sp.add_argument("tool")
    sp.add_argument("source_dir", metavar="ORDNER")
    sp.add_argument("--version", help="Version, falls nicht in pyproject.toml")
    sp.add_argument("--ref", help="Bezeichnung des Stands (Standard: v<Version>)")
    sp.set_defaults(func=_cmd_bundle)
    for name, func, text in [("status", _cmd_status, "läuft das Tool?"),
                             ("stop", _cmd_stop, "Tool beenden"),
                             ("start", _cmd_start, "Tool starten"),
                             ("uninstall", _cmd_uninstall, "Tool deinstallieren")]:
        sp = sub.add_parser(name, help=text)
        sp.add_argument("tool")
        sp.set_defaults(func=func)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
