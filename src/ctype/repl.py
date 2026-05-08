"""Interactive REPL for ctype.

Useful for tweaking themes / settings without re-invoking the CLI.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ctype import __version__
from ctype.config import (
    AVAILABLE_THEMES,
    CONFIG_FILE,
    DEFAULT_SETTINGS,
    coerce_value,
    save_settings,
)
from ctype.renderer import render_file

if TYPE_CHECKING:
    from rich.console import Console

_POSIX_SHLEX = os.name != "nt"

REPL_HELP = """\
Available commands:
  <path> [<path> ...]     Display one or more files
  :theme <name>           Set theme (e.g. monokai, dracula, github-dark)
  :themes                 List curated themes
  :set <key> <value>      Set a setting (line_numbers, tab_size, word_wrap, ...)
  :show                   Show current settings
  :save                   Persist current settings to disk
  :reset                  Reset settings to built-in defaults (in-memory)
  :help / ?               Show this help
  :quit / exit            Leave the REPL
"""


def _print_themes(console: Console) -> None:
    from rich.columns import Columns
    console.print(Columns(AVAILABLE_THEMES, equal=True, expand=True, title="Themes"))


def _print_settings(console: Console, settings: dict[str, Any]) -> None:
    from rich.table import Table
    table = Table(title="ctype settings", caption=f"Stored at: {CONFIG_FILE}")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    for k in DEFAULT_SETTINGS:
        table.add_row(k, repr(settings.get(k, DEFAULT_SETTINGS[k])))
    console.print(table)


def run_repl(console: Console, settings: dict[str, Any]) -> int:
    """Run the interactive loop. Returns the eventual exit code."""
    console.print(
        f"[bold cyan]ctype[/] [dim]v{__version__}[/] — interactive mode. "
        "Type [yellow]:help[/] for commands, [yellow]:quit[/] to exit.",
    )
    while True:
        try:
            raw = input("ctype> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0

        if not raw:
            continue
        if raw in {":quit", ":q", "exit", "quit"}:
            return 0
        if raw in {":help", "?"}:
            console.print(REPL_HELP)
            continue
        if raw == ":themes":
            _print_themes(console)
            continue
        if raw == ":show":
            _print_settings(console, settings)
            continue
        if raw == ":save":
            path = save_settings(settings)
            console.print(f"[green]Saved to {path}[/]")
            continue
        if raw == ":reset":
            settings.clear()
            settings.update(DEFAULT_SETTINGS)
            console.print("[green]Settings reset (use [yellow]:save[/] to persist).[/]")
            continue

        if raw.startswith(":theme "):
            settings["theme"] = raw.removeprefix(":theme ").strip()
            console.print(f"theme = [cyan]{settings['theme']}[/]")
            continue

        if raw.startswith(":set "):
            try:
                parts = shlex.split(raw, posix=_POSIX_SHLEX)
            except ValueError as exc:
                console.print(f"[red]Parse error: {exc}[/]")
                continue
            if len(parts) != 3:  # noqa: PLR2004
                console.print("[red]Usage: :set KEY VALUE[/]")
                continue
            _, key, value = parts
            try:
                settings[key] = coerce_value(key, value)
            except (KeyError, ValueError) as exc:
                console.print(f"[red]{exc}[/]")
                continue
            console.print(f"{key} = {settings[key]!r}")
            continue

        if raw.startswith(":"):
            console.print(f"[red]Unknown command: {raw.split()[0]}[/] (try [yellow]:help[/])")
            continue

        # Treat the rest as one or more file paths
        try:
            tokens = shlex.split(raw, posix=_POSIX_SHLEX)
        except ValueError as exc:
            console.print(f"[red]Parse error: {exc}[/]")
            continue
        for token in tokens:
            render_file(
                console,
                Path(token),
                theme=settings["theme"],
                line_numbers=settings["line_numbers"],
                background_color=settings["background_color"],
                tab_size=settings["tab_size"],
                word_wrap=settings["word_wrap"],
            )
