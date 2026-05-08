# AGENTS.md

## Purpose

`ctype` is a small CLI that prints files with syntax highlighting using `rich`. It is meant to be installed once with `uv tool install` and used everywhere as a drop-in replacement for `type`/`cat`.

## Architecture

- Pure Python, packaged with `hatchling` from a single `pyproject.toml` (no `requirements.txt`, no `setup.py`).
- Layout is `src/`-based:
  - `src/ctype/__init__.py` — version constant only.
  - `src/ctype/__main__.py` — enables `python -m ctype`.
  - `src/ctype/cli.py` — argparse schema and the `main()` entry point. Heavy imports (`rich`) are deferred until needed so `--help` and `--version` are effectively instant.
  - `src/ctype/config.py` — persisted settings at `~/.ctype/config.json`, plus the curated theme list and a `coerce_value` helper.
  - `src/ctype/renderer.py` — `render_file` / `render_text` wrappers around `rich.syntax.Syntax`. Handles binary-file detection and read errors.
  - `src/ctype/repl.py` — interactive `:`-prefixed command loop.
- The console-script entry point `ctype = "ctype.cli:main"` is what `uv tool install` turns into a `.exe` shim on Windows.

## Conventions

- New CLI flags belong in `build_parser()` in `cli.py` and should be wired through `_apply_overrides()` if they should also stack on top of persisted config.
- New persisted settings: add to `DEFAULT_SETTINGS` in `config.py` (and to `_BOOL_KEYS` / `_INT_KEYS` / `_OPTIONAL_STR_KEYS` if they need coercion). The REPL `:set` and CLI `--config-set` pick them up automatically.
- New REPL commands are `:`-prefixed and dispatched in `run_repl()` in `repl.py`.
- Lazy-import `rich.*` inside functions, not at module top-level — this is what keeps `ctype --help` snappy without a compiled binary.
- Lint with `ruff check` and `ruff format` (config in `pyproject.toml`, medium strictness — no docstring-style enforcement).
