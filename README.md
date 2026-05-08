# ctype

A cross-platform replacement for Windows `type` (and a friendlier `cat`) that prints files with proper syntax highlighting via [`rich`](https://github.com/Textualize/rich). Auto-detects the lexer from the file extension, so `.py`, `.cs`, `.js`, `.ts`, `.json`, `.toml`, `.html`, `.css`, `.md`, `.rs`, `.go`, `.sh` and ~hundreds of other formats Pygments knows about Just Work.

## Install

```bash
uv tool install --from . ctype
# or, if published to a wheel index:
uv tool install ctype
```

`uv tool install` drops a fast `ctype.exe` shim into your user `~/.local/bin` (or `%USERPROFILE%\.local\bin` on Windows), which `uv` adds to your `PATH`.

## Examples

```bash
ctype src/ctype/cli.py                  # auto-highlight a python file
ctype foo.cs bar.js baz.py              # multiple files
ctype --theme github-dark main.rs       # one-off theme override
ctype -n -r 1:40 main.cs                # line numbers, lines 1..40
ctype -l json < payload.txt             # pipe stdin, force a lexer
ctype src/                              # directory → rich tree view
ctype --tree-depth 5 -a node_modules    # deeper tree, include hidden
ctype -x image.png                      # colored hex/ASCII dump
ctype -w live.log                       # tail-f-style watch, redraws on change
ctype --config-set theme dracula        # persist your favourite theme
ctype --config-set line_numbers true    # …or always show line numbers
ctype --list-themes                     # browse available themes
ctype --repl                            # interactive mode
```

Binary files are auto-detected and rendered as a hex dump unless you force a lexer with `-l`. Pass `-x` to force hex on a text file too.

Run `ctype --help` for the full argparse schema, or `:help` inside the REPL.
