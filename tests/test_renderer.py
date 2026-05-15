"""Tests for ctype.renderer — file/tree/hex rendering and binary detection."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from ctype.renderer import (
    looks_binary,
    render_file,
    render_hex,
    render_tree,
    render_tree_contents,
)


def _render_tree_contents_defaults(console, root, *, max_depth=None, show_hidden=False):
    return render_tree_contents(
        console,
        root,
        max_depth=max_depth,
        show_hidden=show_hidden,
        theme="monokai",
        line_numbers=False,
        background_color=None,
        tab_size=4,
        word_wrap=False,
    )


def _capture_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, force_terminal=False, color_system=None, width=120), buf


def test_looks_binary_detects_nul_bytes(tmp_path):
    f = tmp_path / "bin"
    f.write_bytes(b"hello\x00world")
    assert looks_binary(f) is True


def test_looks_binary_rejects_text(tmp_path):
    f = tmp_path / "txt"
    f.write_text("hello world\n")
    assert looks_binary(f) is False


def test_looks_binary_handles_missing_file(tmp_path):
    assert looks_binary(tmp_path / "does-not-exist") is False


def test_render_hex_outputs_offset_and_ascii(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"ABCDEF")
    console, buf = _capture_console()
    rc = render_hex(console, f)
    assert rc == 0
    out = buf.getvalue()
    assert "00000000" in out
    assert "|ABCDEF|" in out


def test_render_hex_truncates_at_max_bytes(tmp_path):
    f = tmp_path / "big.bin"
    f.write_bytes(b"X" * 1000)
    console, buf = _capture_console()
    rc = render_hex(console, f, max_bytes=32)
    assert rc == 0
    out = buf.getvalue()
    assert "truncated at 32 bytes" in out


def test_render_hex_errors_on_missing(tmp_path):
    console, _buf = _capture_console()
    rc = render_hex(console, tmp_path / "missing")
    assert rc == 1


def test_render_hex_errors_on_directory(tmp_path):
    console, _buf = _capture_console()
    rc = render_hex(console, tmp_path)
    assert rc == 1


def test_render_tree_lists_visible_children(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").write_text("hi")
    console, buf = _capture_console()
    rc = render_tree(console, tmp_path)
    assert rc == 0
    out = buf.getvalue()
    assert "subdir/" in out
    assert "file.txt" in out


def test_render_tree_skips_hidden_by_default(tmp_path):
    (tmp_path / ".secret").write_text("x")
    (tmp_path / "visible.py").write_text("x")
    console, buf = _capture_console()
    render_tree(console, tmp_path)
    out = buf.getvalue()
    assert "visible.py" in out
    assert ".secret" not in out


def test_render_tree_includes_hidden_when_requested(tmp_path):
    (tmp_path / ".secret").write_text("x")
    console, buf = _capture_console()
    render_tree(console, tmp_path, show_hidden=True)
    assert ".secret" in buf.getvalue()


def test_render_tree_respects_max_depth(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "leaf.txt").write_text("x")
    console, buf = _capture_console()
    render_tree(console, tmp_path, max_depth=1)
    out = buf.getvalue()
    assert "a/" in out
    assert "leaf.txt" not in out


def test_render_tree_errors_on_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi")
    console, _buf = _capture_console()
    assert render_tree(console, f) == 1


@pytest.mark.parametrize("missing", ["nope.py", "still-no.py"])
def test_render_file_errors_on_missing(tmp_path, missing):
    console, _buf = _capture_console()
    rc = render_file(
        console,
        tmp_path / missing,
        theme="monokai",
        line_numbers=False,
        background_color=None,
        tab_size=4,
        word_wrap=False,
    )
    assert rc == 1


def test_render_tree_contents_dumps_text_and_skips_binary(tmp_path):
    (tmp_path / "snippet.py").write_text("answer = 42\n")
    (tmp_path / "notes.txt").write_text("hello there\n")
    (tmp_path / "blob.bin").write_bytes(b"AB\x00CD")
    console, buf = _capture_console()
    rc = _render_tree_contents_defaults(console, tmp_path)
    assert rc == 0
    out = buf.getvalue()
    assert "snippet.py" in out
    assert "notes.txt" in out
    assert "blob.bin" in out
    assert "answer = 42" in out
    assert "hello there" in out
    assert "<binary file, skipped>" in out


def test_render_tree_contents_skips_hidden_by_default(tmp_path):
    (tmp_path / ".hidden.py").write_text("secret = 1\n")
    (tmp_path / "visible.py").write_text("shown = 2\n")
    console, buf = _capture_console()
    _render_tree_contents_defaults(console, tmp_path)
    out = buf.getvalue()
    assert "shown = 2" in out
    assert "secret = 1" not in out


def test_render_tree_contents_includes_hidden_when_requested(tmp_path):
    (tmp_path / ".hidden.py").write_text("secret = 1\n")
    console, buf = _capture_console()
    _render_tree_contents_defaults(console, tmp_path, show_hidden=True)
    assert "secret = 1" in buf.getvalue()


def test_render_tree_contents_respects_max_depth(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (tmp_path / "top.py").write_text("top_val = 1\n")
    (nested / "deep.py").write_text("deep_val = 2\n")
    console, buf = _capture_console()
    _render_tree_contents_defaults(console, tmp_path, max_depth=1)
    out = buf.getvalue()
    assert "top_val = 1" in out
    assert "deep_val = 2" not in out


def test_render_tree_contents_errors_on_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi")
    console, _buf = _capture_console()
    assert _render_tree_contents_defaults(console, f) == 1


def test_render_file_renders_python_source(tmp_path):
    f = tmp_path / "snippet.py"
    f.write_text("x = 42\n")
    console, buf = _capture_console()
    rc = render_file(
        console,
        f,
        theme="monokai",
        line_numbers=False,
        background_color=None,
        tab_size=4,
        word_wrap=False,
    )
    assert rc == 0
    assert "42" in buf.getvalue()
