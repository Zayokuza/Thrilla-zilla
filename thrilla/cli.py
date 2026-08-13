"""Command-line entry point for interactive and scriptable Thrilla use."""

import argparse
import json
from typing import Optional, Sequence

from . import __version__
from .app import ThrillaApp, checks_as_dicts
from .colors import ColorMode, Palette
from .config import Config
from .diagnostics import run_checks
from .donors import DonorRegistry
from .router import route_request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thrilla",
        description="Thrilla-zilla phone-first local AI workbench",
    )
    parser.add_argument("--version", action="version", version=f"Thrilla-zilla {__version__}")
    parser.add_argument("--color", choices=[mode.value for mode in ColorMode], help="override color mode")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("menu", help="open the interactive menu")
    subparsers.add_parser("chat", help="open the routed local-model chat")

    route = subparsers.add_parser("route", help="explain how a request will be routed")
    route.add_argument("text", nargs="+", help="request text")
    route.add_argument("--json", action="store_true", help="machine-readable output")

    donors = subparsers.add_parser("donors", help="show donor-library status")
    donors.add_argument("--phase", type=int, choices=(1, 2), default=1)
    donors.add_argument("--priority", action="store_true")
    donors.add_argument("--problems", action="store_true")
    donors.add_argument("--json", action="store_true")

    doctor = subparsers.add_parser("doctor", help="run environment checks")
    doctor.add_argument("--no-model", action="store_true", help="skip model network check")
    doctor.add_argument("--json", action="store_true")

    logs = subparsers.add_parser("logs", help="show recent activity metadata")
    logs.add_argument("-n", "--count", type=int, default=20)
    logs.add_argument("--json", action="store_true")
    return parser


def _config_for(arguments: argparse.Namespace) -> Config:
    config = Config.load()
    if arguments.color:
        config.color_mode = arguments.color
    return config


def _donor_command(arguments: argparse.Namespace, config: Config) -> int:
    registry = DonorRegistry(config.donor_path)
    states = registry.scan(arguments.phase)
    if arguments.priority:
        states = tuple(state for state in states if state.spec.priority)
    if arguments.problems:
        states = tuple(state for state in states if not state.present)
    ready = sum(state.present for state in states)
    if arguments.json:
        print(json.dumps({
            "root": str(registry.root),
            "ready": ready,
            "total": len(states),
            "repositories": [
                {
                    "repository": state.spec.repository,
                    "path": str(state.path),
                    "state": state.state,
                    "priority": state.spec.priority,
                }
                for state in states
            ],
        }, indent=2))
        return 0 if ready == len(states) else 1
    palette = Palette(ColorMode(config.color_mode))
    print(palette.brand(f"Thrilla donor library • Phase {arguments.phase}"))
    print(f"Root: {registry.root}")
    print(f"Ready: {ready}/{len(states)}")
    for state in states:
        marker = palette.success("✓") if state.present else palette.error("✗")
        print(f"{marker} {state.spec.repository} [{state.state}]")
    return 0 if ready == len(states) else 1


def _doctor_command(arguments: argparse.Namespace, config: Config) -> int:
    checks = run_checks(config, include_model=not arguments.no_model)
    if arguments.json:
        print(json.dumps(checks_as_dicts(checks), indent=2))
    else:
        palette = Palette(ColorMode(config.color_mode))
        for check in checks:
            painter = {"pass": palette.success, "warn": palette.warning, "fail": palette.error}[check.level]
            marker = {"pass": "✓", "warn": "!", "fail": "✗"}[check.level]
            print(f"{painter(marker)} {check.name}: {check.detail}")
    return 1 if any(check.level == "fail" for check in checks) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    config = _config_for(arguments)
    command = arguments.command or "menu"
    if command == "menu":
        return ThrillaApp(config).run()
    if command == "chat":
        ThrillaApp(config).ask()
        return 0
    if command == "route":
        decision = route_request(" ".join(arguments.text))
        payload = {
            "route": decision.route.value,
            "confidence": decision.confidence,
            "matches": list(decision.matches),
            "explanation": decision.explanation,
        }
        if arguments.json:
            print(json.dumps(payload, indent=2))
        else:
            palette = Palette(ColorMode(config.color_mode))
            print(palette.accent(f"Route: {decision.route.value}"))
            print(f"Confidence: {decision.confidence:.0%}")
            print(f"Why: {decision.explanation}")
        return 0
    if command == "donors":
        return _donor_command(arguments, config)
    if command == "doctor":
        return _doctor_command(arguments, config)
    if command == "logs":
        records = ThrillaApp(config).audit.tail(max(0, arguments.count))
        print(json.dumps(records, indent=2) if arguments.json else "\n".join(json.dumps(record) for record in records))
        return 0
    parser.error(f"Unknown command: {command}")
    return 2
