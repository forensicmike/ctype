"""Tests for ctype.config — settings persistence and value coercion."""

from __future__ import annotations

import json

import pytest

from ctype import config as cfg


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR/CONFIG_FILE into a temporary location."""
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.json")
    return tmp_path


def test_load_returns_defaults_when_missing(isolated_config):
    assert cfg.load_settings() == cfg.DEFAULT_SETTINGS


def test_save_then_load_roundtrip(isolated_config):
    settings = dict(cfg.DEFAULT_SETTINGS)
    settings["theme"] = "dracula"
    settings["line_numbers"] = True
    settings["tab_size"] = 8

    cfg.save_settings(settings)
    loaded = cfg.load_settings()

    assert loaded["theme"] == "dracula"
    assert loaded["line_numbers"] is True
    assert loaded["tab_size"] == 8


def test_load_ignores_unknown_keys(isolated_config):
    cfg.CONFIG_FILE.write_text(json.dumps({"theme": "vim", "bogus": 42}))
    loaded = cfg.load_settings()
    assert loaded["theme"] == "vim"
    assert "bogus" not in loaded


def test_load_handles_corrupt_file(isolated_config):
    cfg.CONFIG_FILE.write_text("{ this is not json")
    assert cfg.load_settings() == cfg.DEFAULT_SETTINGS


def test_load_handles_non_dict_payload(isolated_config):
    cfg.CONFIG_FILE.write_text(json.dumps([1, 2, 3]))
    assert cfg.load_settings() == cfg.DEFAULT_SETTINGS


def test_save_drops_unknown_keys(isolated_config):
    cfg.save_settings({**cfg.DEFAULT_SETTINGS, "theme": "vim", "bogus": 99})
    written = json.loads(cfg.CONFIG_FILE.read_text())
    assert "bogus" not in written
    assert written["theme"] == "vim"


def test_coerce_value_booleans():
    assert cfg.coerce_value("line_numbers", "true") is True
    assert cfg.coerce_value("line_numbers", "TRUE") is True
    assert cfg.coerce_value("line_numbers", "1") is True
    assert cfg.coerce_value("line_numbers", "yes") is True
    assert cfg.coerce_value("line_numbers", "on") is True
    assert cfg.coerce_value("line_numbers", "0") is False
    assert cfg.coerce_value("line_numbers", "off") is False


def test_coerce_value_int():
    assert cfg.coerce_value("tab_size", "8") == 8


def test_coerce_value_optional_string():
    assert cfg.coerce_value("background_color", "none") is None
    assert cfg.coerce_value("background_color", "null") is None
    assert cfg.coerce_value("background_color", "default") is None
    assert cfg.coerce_value("background_color", "#222") == "#222"


def test_coerce_value_passthrough_string():
    assert cfg.coerce_value("theme", "dracula") == "dracula"


def test_coerce_value_unknown_key_raises():
    with pytest.raises(KeyError):
        cfg.coerce_value("not_a_setting", "x")


def test_coerce_value_invalid_int_raises():
    with pytest.raises(ValueError):  # noqa: PT011
        cfg.coerce_value("tab_size", "not-a-number")
