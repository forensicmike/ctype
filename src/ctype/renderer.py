"""File rendering helpers, isolated so they're easy to call from the API layer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console


def _looks_binary(path: Path, sniff_bytes: int = 4096) -> bool:
    """Return True if the file contains a NUL byte in its first chunk."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(sniff_bytes)
    except OSError:
        return False
    return b"\x00" in chunk


def render_file(
    console: Console,
    path: Path,
    *,
    theme: str,
    line_numbers: bool,
    background_color: str | None,
    tab_size: int,
    word_wrap: bool,
    language: str | None = None,
    line_range: tuple[int, int] | None = None,
) -> int:
    """Render a file to ``console``. Returns 0 on success, non-zero on error."""
    from rich.syntax import Syntax  # lazy: keep --help fast

    if not path.exists():
        console.print(f"[red]ctype: {path}: No such file or directory[/]")
        return 1
    if path.is_dir():
        console.print(f"[red]ctype: {path}: Is a directory[/]")
        return 1
    if _looks_binary(path):
        console.print(f"[yellow]ctype: {path}: binary file, skipping[/]")
        return 2

    common: dict[str, Any] = {
        "theme": theme,
        "line_numbers": line_numbers,
        "tab_size": tab_size,
        "word_wrap": word_wrap,
    }
    if background_color is not None:
        common["background_color"] = background_color
    if line_range is not None:
        common["line_range"] = line_range

    try:
        if language:
            code = path.read_text(encoding="utf-8", errors="replace")
            syntax = Syntax(code, language, **common)
        else:
            syntax = Syntax.from_path(str(path), **common)
    except OSError as exc:
        console.print(f"[red]ctype: {path}: {exc}[/]")
        return 1

    console.print(syntax)
    return 0


def render_text(
    console: Console,
    text: str,
    *,
    language: str,
    theme: str,
    line_numbers: bool,
    background_color: str | None,
    tab_size: int,
    word_wrap: bool,
) -> None:
    """Render an in-memory string (e.g. piped stdin) with syntax highlighting."""
    from rich.syntax import Syntax

    common: dict[str, Any] = {
        "theme": theme,
        "line_numbers": line_numbers,
        "tab_size": tab_size,
        "word_wrap": word_wrap,
    }
    if background_color is not None:
        common["background_color"] = background_color
    console.print(Syntax(text, language, **common))
