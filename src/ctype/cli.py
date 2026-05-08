"""CLI entry point for ctype.

Heavy imports (rich, etc.) are deferred so that ``ctype --help`` and
``ctype --version`` return effectively instantly even without a compiled exe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ctype import __version__
from ctype.config import (
    AVAILABLE_THEMES,
    CONFIG_FILE,
    DEFAULT_SETTINGS,
    coerce_value,
    load_settings,
    save_settings,
)

if TYPE_CHECKING:
    from rich.console import Console


def _parse_range(spec: str) -> tuple[int, int]:
    """Parse a 'START:END' range argument."""
    if ":" not in spec:
        msg = f"Invalid range '{spec}', expected START:END"
        raise argparse.ArgumentTypeError(msg)
    start_s, end_s = spec.split(":", 1)
    try:
        start, end = int(start_s), int(end_s)
    except ValueError as exc:
        msg = f"Invalid range '{spec}': {exc}"
        raise argparse.ArgumentTypeError(msg) from exc
    if start < 1 or end < start:
        msg = f"Invalid range '{spec}': require 1 <= START <= END"
        raise argparse.ArgumentTypeError(msg)
    return start, end


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse schema for ctype."""
    parser = argparse.ArgumentParser(
        prog="ctype",
        description=(
            "Cross-platform 'type'/'cat' replacement that syntax-highlights "
            "source files using rich. Reads stdin when no FILE is given."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        metavar="FILE",
        help="One or more files to display.",
    )
    parser.add_argument(
        "-t", "--theme",
        help="Syntax highlighting theme (e.g. monokai, dracula, github-dark).",
    )
    parser.add_argument(
        "-n", "--line-numbers",
        action="store_true",
        default=False,
        help="Show line numbers for this invocation.",
    )
    parser.add_argument(
        "-N", "--no-line-numbers",
        action="store_true",
        help="Hide line numbers for this invocation (overrides saved setting).",
    )
    parser.add_argument(
        "-l", "--language",
        help="Force a specific Pygments lexer (default: auto-detect from extension).",
    )
    parser.add_argument(
        "-r", "--range",
        metavar="START:END",
        type=_parse_range,
        help="Display only lines START..END (1-indexed, inclusive).",
    )
    parser.add_argument(
        "-w", "--word-wrap",
        action="store_true",
        help="Enable word wrap.",
    )
    parser.add_argument(
        "--tab-size",
        type=int,
        help="Number of spaces per tab.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output (plain text).",
    )

    parser.add_argument("--repl", action="store_true", help="Launch the interactive REPL.")
    parser.add_argument("--list-themes", action="store_true", help="List curated themes and exit.")
    parser.add_argument("--config-show", action="store_true", help="Show persisted configuration and exit.")
    parser.add_argument(
        "--config-set",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Persist KEY=VALUE in user config (can be repeated).",
    )
    parser.add_argument(
        "--config-reset",
        action="store_true",
        help="Reset persisted config to defaults and exit.",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"ctype {__version__}",
    )
    return parser


def _list_themes(console: Console) -> int:
    from rich.columns import Columns
    console.print(Columns(AVAILABLE_THEMES, equal=True, expand=True, title="Available themes"))
    return 0


def _show_config(console: Console, settings: dict) -> int:
    from rich.table import Table
    table = Table(title="ctype settings", caption=f"Stored at: {CONFIG_FILE}")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    for key in DEFAULT_SETTINGS:
        table.add_row(key, repr(settings.get(key, DEFAULT_SETTINGS[key])))
    console.print(table)
    return 0


def _apply_overrides(settings: dict, args: argparse.Namespace) -> dict:
    """Layer per-invocation flags on top of persisted settings."""
    effective = dict(settings)
    if args.theme:
        effective["theme"] = args.theme
    if args.line_numbers:
        effective["line_numbers"] = True
    if args.no_line_numbers:
        effective["line_numbers"] = False
    if args.word_wrap:
        effective["word_wrap"] = True
    if args.tab_size is not None:
        effective["tab_size"] = args.tab_size
    return effective


def main(argv: list[str] | None = None) -> int:
    """Run ctype. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()

    # Defer importing rich until we know we'll need it.
    from rich.console import Console
    console = Console(no_color=args.no_color, soft_wrap=False, highlight=False)

    # --- Config-only flags -------------------------------------------------
    if args.config_reset:
        path = save_settings(dict(DEFAULT_SETTINGS))
        console.print(f"[green]Configuration reset to defaults at {path}[/]")
        return 0

    if args.config_set:
        for key, value in args.config_set:
            try:
                settings[key] = coerce_value(key, value)
            except (KeyError, ValueError) as exc:
                console.print(f"[red]{exc}[/]")
                return 2
        save_settings(settings)
        console.print("[green]Configuration updated.[/]")
        return 0

    if args.list_themes:
        return _list_themes(console)
    if args.config_show:
        return _show_config(console, settings)

    effective = _apply_overrides(settings, args)

    # --- REPL --------------------------------------------------------------
    if args.repl:
        from ctype.repl import run_repl
        return run_repl(console, effective)

    # --- Stdin pipe --------------------------------------------------------
    if not args.files:
        if not sys.stdin.isatty():
            from ctype.renderer import render_text
            render_text(
                console,
                sys.stdin.read(),
                language=args.language or "text",
                theme=effective["theme"],
                line_numbers=effective["line_numbers"],
                background_color=effective["background_color"],
                tab_size=effective["tab_size"],
                word_wrap=effective["word_wrap"],
            )
            return 0
        parser.print_help()
        return 1

    # --- Files -------------------------------------------------------------
    from ctype.renderer import render_file

    rc = 0
    for path in args.files:
        result = render_file(
            console,
            path,
            theme=effective["theme"],
            line_numbers=effective["line_numbers"],
            background_color=effective["background_color"],
            tab_size=effective["tab_size"],
            word_wrap=effective["word_wrap"],
            language=args.language,
            line_range=args.range,
        )
        if result and not rc:
            rc = result
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
