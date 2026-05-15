"""Tests for ctype.cli — argparse schema and helpers."""

from __future__ import annotations

import argparse

import pytest

from ctype.cli import _parse_range, build_parser


def test_parser_minimal():
    parser = build_parser()
    ns = parser.parse_args(["foo.py"])
    assert [str(p) for p in ns.files] == ["foo.py"]
    assert ns.hex is False
    assert ns.watch is False
    assert ns.tree_depth == 3
    assert ns.all is False


def test_parser_combined_flags():
    parser = build_parser()
    ns = parser.parse_args(
        [
            "-w",
            "-x",
            "--tree-depth",
            "5",
            "-a",
            "--watch-interval",
            "0.5",
            "--hex-max",
            "256",
            "x.bin",
        ]
    )
    assert ns.watch is True
    assert ns.hex is True
    assert ns.tree_depth == 5
    assert ns.all is True
    assert ns.watch_interval == pytest.approx(0.5)
    assert ns.hex_max == 256


def test_parser_config_set_appends():
    parser = build_parser()
    ns = parser.parse_args(
        [
            "--config-set",
            "theme",
            "dracula",
            "--config-set",
            "tab_size",
            "8",
        ]
    )
    assert ns.config_set == [["theme", "dracula"], ["tab_size", "8"]]


def test_parser_range_parsed():
    parser = build_parser()
    ns = parser.parse_args(["-r", "10:20", "x.py"])
    assert ns.range == (10, 20)


def test_parser_contents_flag():
    parser = build_parser()
    ns = parser.parse_args(["-c", "."])
    assert ns.contents is True
    ns2 = parser.parse_args(["."])
    assert ns2.contents is False


def test_parse_range_valid():
    assert _parse_range("1:10") == (1, 10)
    assert _parse_range("5:5") == (5, 5)


@pytest.mark.parametrize("spec", ["nope", "5:1", "0:5", "abc:def", "1:", ":5"])
def test_parse_range_rejects_invalid(spec):
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_range(spec)
