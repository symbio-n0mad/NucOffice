"""Kommandozeile von NucOffice (die PySide6-Oberfläche folgt und nutzt denselben Kern)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__, installer, process
from .sources import github
from .paths import Scope, layout
from .registry import load_registry
from .state import State


def _cmd_list(args) -> int:
    reg = load_registry()
    state = State(layout(args.scope).state_file)
    for key, tool in reg.items():
        inst = state.get(key)
        version = inst.version if inst else "–"
        running = "läuft" if process.status(key) else ""
        note = "" if tool.supported else "(auf diesem System nicht verfügbar)"
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


def _cmd_install(args) -> int:
    tool, lay = _get_tool(args.tool), layout(args.scope)
    try:
        if args.source_path:
            installer.install(tool, Path(args.source_path), lay, source="local", ref="local")
        else:
            rel = github.latest(tool.repo)
            print(f"Lade {tool.display_name} {rel.ref} ({rel.commit[:10]}) von GitHub …")
            src = github.download_source(tool.repo, rel.commit, lay.staging_dir / tool.key)
            try:
                installer.install(tool, src, lay, source="github", ref=rel.ref, commit=rel.commit)
            finally:
                shutil.rmtree(src, ignore_errors=True)
    except (installer.InstallError, OSError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nucoffice", description="NC-Tools verwalten")
    p.add_argument("--version", action="version", version=f"NucOffice {__version__}")
    p.add_argument("--system", dest="scope", action="store_const", const=Scope.SYSTEM,
                   default=Scope.USER, help="systemweite Installation verwenden")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="alle Tools mit Status").set_defaults(func=_cmd_list)
    sp = sub.add_parser("install", help="Tool installieren oder aktualisieren (neueste Version)")
    sp.add_argument("tool")
    sp.add_argument("--from", dest="source_path", metavar="ORDNER",
                    help="aus lokalem Quellordner statt von GitHub installieren")
    sp.set_defaults(func=_cmd_install)
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
