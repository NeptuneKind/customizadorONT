"""Tests for settings load/merge/save logic."""
import json

import pytest

from config.settings import (
    DEFAULT_SETTINGS,
    get_settings_path,
    load_or_init_settings,
    resolve_headless,
    save_settings,
)


@pytest.mark.unit
class TestLoadSettings:
    """Tests for settings initialization and loading."""

    def test_load_creates_default_when_no_file(self, tmp_path):
        """When settings.json doesn't exist, defaults are created."""
        result = load_or_init_settings(PROJECT_ROOT=tmp_path, CONFIG_DIR=tmp_path)
        assert result["headless"] is False
        assert "huawei" in result["login_candidates"]
        assert (tmp_path / "settings.json").exists()

    def test_load_merges_partial_file(self, tmp_path):
        """An existing file with missing keys gets merged with defaults."""
        partial = {"headless": True}
        (tmp_path / "settings.json").write_text(json.dumps(partial))
        result = load_or_init_settings(PROJECT_ROOT=tmp_path, CONFIG_DIR=tmp_path)
        assert result["headless"] is True
        assert "login_candidates" in result
        assert "huawei" in result["login_candidates"]

    def test_load_corrupted_returns_defaults(self, tmp_path):
        """A corrupted JSON returns defaults without crashing."""
        (tmp_path / "settings.json").write_text("NOT VALID JSON {{{")
        result = load_or_init_settings(PROJECT_ROOT=tmp_path, CONFIG_DIR=tmp_path)
        assert result["headless"] is False
        assert "login_candidates" in result


@pytest.mark.unit
class TestSaveSettings:
    """Tests for settings persistence."""

    def test_save_settings_roundtrip(self, tmp_path):
        """Save then load yields the same dict."""
        original = dict(DEFAULT_SETTINGS)
        original["headless"] = True
        save_settings(CONFIG_DIR=tmp_path, settings=original)

        loaded = load_or_init_settings(PROJECT_ROOT=tmp_path, CONFIG_DIR=tmp_path)
        assert loaded["headless"] is True


@pytest.mark.unit
class TestResolveHeadless:
    """Tests for CLI/settings headless resolution."""

    def test_cli_headless_wins(self):
        """--headless flag overrides settings."""
        from types import SimpleNamespace
        args = SimpleNamespace(headless=True, no_headless=False)
        assert resolve_headless({"headless": False}, args) is True

    def test_cli_no_headless_wins(self):
        """--no-headless flag overrides settings."""
        from types import SimpleNamespace
        args = SimpleNamespace(headless=False, no_headless=True)
        assert resolve_headless({"headless": True}, args) is False

    def test_settings_fallback(self):
        """No CLI flags → use settings value."""
        from types import SimpleNamespace
        args = SimpleNamespace(headless=False, no_headless=False)
        assert resolve_headless({"headless": True}, args) is True

    def test_both_flags_headless_wins(self):
        """If both CLI flags are set, headless wins."""
        from types import SimpleNamespace
        args = SimpleNamespace(headless=True, no_headless=True)
        assert resolve_headless({"headless": False}, args) is True
