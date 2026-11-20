"""Kommandozeile von NucOffice (die PySide6-Oberfläche folgt und nutzt denselben Kern)."""

from __future__ import annotations

import argparse
import sys

from . import __version__, process
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nucoffice", description="NC-Tools verwalten")
    p.add_argument("--version", action="version", version=f"NucOffice {__version__}")
    p.add_argument("--system", dest="scope", action="store_const", const=Scope.SYSTEM,
                   default=Scope.USER, help="systemweite Installation verwenden")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="alle Tools mit Status").set_defaults(func=_cmd_list)
    for name, func, text in [("status", _cmd_status, "läuft das Tool?"),
                             ("stop", _cmd_stop, "Tool beenden")]:
        sp = sub.add_parser(name, help=text)
        sp.add_argument("tool")
        sp.set_defaults(func=func)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
