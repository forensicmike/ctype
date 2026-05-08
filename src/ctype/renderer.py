"""File rendering helpers, isolated so they're easy to call from the API layer."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console


def looks_binary(path: Path, sniff_bytes: int = 4096) -> bool:
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


# ---------------------------------------------------------------------------
# Directory tree
# ---------------------------------------------------------------------------


def render_tree(
    console: Console,
    root: Path,
    *,
    max_depth: int | None = 3,
    show_hidden: bool = False,
) -> int:
    """Render a directory listing as a rich.tree."""
    from rich.tree import Tree

    if not root.exists():
        console.print(f"[red]ctype: {root}: No such file or directory[/]")
        return 1
    if not root.is_dir():
        console.print(f"[red]ctype: {root}: Not a directory[/]")
        return 1

    tree = Tree(f"[bold cyan]{root}[/]")
    _walk_tree(root, tree, depth=0, max_depth=max_depth, show_hidden=show_hidden)
    console.print(tree)
    return 0


def _walk_tree(
    path: Path,
    parent: Any,
    *,
    depth: int,
    max_depth: int | None,
    show_hidden: bool,
) -> None:
    if max_depth is not None and depth >= max_depth:
        return
    try:
        children = sorted(
            path.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
    except (PermissionError, OSError) as exc:
        parent.add(f"[red]<{exc.__class__.__name__}>[/]")
        return
    for child in children:
        if not show_hidden and child.name.startswith("."):
            continue
        if child.is_dir():
            sub = parent.add(f"[bold blue]{child.name}/[/]")
            _walk_tree(
                child,
                sub,
                depth=depth + 1,
                max_depth=max_depth,
                show_hidden=show_hidden,
            )
        else:
            parent.add(child.name)


# ---------------------------------------------------------------------------
# Hex dump
# ---------------------------------------------------------------------------

_HEX_BYTES_PER_ROW = 16


def _byte_style(b: int) -> str:
    if b == 0x00:
        return "dim"
    if b < 0x20 or b == 0x7F:
        return "magenta"
    if b >= 0x80:  # noqa: PLR2004
        return "yellow"
    return ""


def render_hex(console: Console, path: Path, *, max_bytes: int | None = None) -> int:
    """Render a file as a colored xxd-style hex dump."""
    from rich.text import Text

    if not path.exists():
        console.print(f"[red]ctype: {path}: No such file or directory[/]")
        return 1
    if path.is_dir():
        console.print(f"[red]ctype: {path}: Is a directory[/]")
        return 1
    try:
        data = path.read_bytes()
    except OSError as exc:
        console.print(f"[red]ctype: {path}: {exc}[/]")
        return 1

    if max_bytes is not None and len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    else:
        truncated = False

    bpr = _HEX_BYTES_PER_ROW
    for offset in range(0, len(data), bpr):
        chunk = data[offset : offset + bpr]
        line = Text()
        line.append(f"{offset:08x}  ", style="dim cyan")
        for i, b in enumerate(chunk):
            line.append(f"{b:02x}", style=_byte_style(b))
            line.append("  " if i == (bpr // 2) - 1 else " ")
        # Pad short final row so the ASCII column stays aligned.
        missing = bpr - len(chunk)
        if missing:
            pad = missing * 3
            if len(chunk) <= bpr // 2:
                pad += 1
            line.append(" " * pad)
        line.append(" |")
        for b in chunk:
            ch = chr(b) if 0x20 <= b < 0x7F else "."  # noqa: PLR2004
            line.append(ch, style=_byte_style(b))
        line.append("|")
        console.print(line)

    if truncated:
        console.print(f"[dim]... truncated at {max_bytes} bytes[/]")
    return 0


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------


def watch_file(
    console: Console,
    path: Path,
    render_once: Callable[[], int],
    *,
    interval: float = 0.25,
) -> int:
    """Re-run ``render_once`` whenever ``path``'s mtime changes. Ctrl-C exits."""
    last_mtime: float | None = None
    last_missing = False
    try:
        while True:
            try:
                mtime = path.stat().st_mtime
                missing = False
            except FileNotFoundError:
                mtime = None
                missing = True

            if missing != last_missing or mtime != last_mtime:
                console.clear()
                stamp = time.strftime("%H:%M:%S")
                console.rule(f"[bold]{path}[/] [dim]· watching · {stamp}[/]")
                if missing:
                    console.print(f"[yellow]ctype: {path}: not found (waiting)[/]")
                else:
                    render_once()
                last_mtime = mtime
                last_missing = missing
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print()
        return 0
