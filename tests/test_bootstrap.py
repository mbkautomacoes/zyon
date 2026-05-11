"""Tests for bootstrap.py orchestration helpers."""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "bootstrap",
    pathlib.Path(__file__).parent.parent / "scripts" / "bootstrap.py",
)
bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bootstrap)

extract_quick_tunnel_url = bootstrap.extract_quick_tunnel_url

import pytest


def test_extract_url_from_cloudflared_log_quick_tunnel():
    log = """
2026-04-28T20:00:00Z INF Starting tunnel tunnelID=
2026-04-28T20:00:01Z INF |  Your quick Tunnel has been created! Visit it at:  |
2026-04-28T20:00:01Z INF |  https://random-words-1234.trycloudflare.com        |
2026-04-28T20:00:02Z INF Registered tunnel connection
"""
    assert extract_quick_tunnel_url(log) == "https://random-words-1234.trycloudflare.com"


def test_extract_url_returns_none_when_absent():
    log = "2026-04-28T20:00:00Z INF Starting tunnel\n2026-04-28T20:00:01Z INF Registered\n"
    assert extract_quick_tunnel_url(log) is None


def test_extract_url_strips_box_borders_and_whitespace():
    log = "|  https://abc-def-1234.trycloudflare.com  |"
    assert extract_quick_tunnel_url(log) == "https://abc-def-1234.trycloudflare.com"


def test_main_is_callable():
    assert callable(bootstrap.main)
    assert callable(bootstrap.find_cloudflared)


def test_find_cloudflared_returns_none(monkeypatch, tmp_path):
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "which", lambda _: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert bootstrap.find_cloudflared() is None


def test_find_beads_returns_none_when_missing(monkeypatch):
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "which", lambda _: None)
    assert bootstrap.find_beads() is None


def test_ensure_beads_skips_when_dir_exists(monkeypatch, tmp_path):
    import shutil as _shutil
    fake_bd = tmp_path / "bd"
    fake_bd.write_text("")
    monkeypatch.setattr(_shutil, "which", lambda _: str(fake_bd))
    (tmp_path / ".beads").mkdir()

    called = {"init": False}

    def fake_check_call(*args, **kwargs):
        called["init"] = True

    monkeypatch.setattr(bootstrap.subprocess, "check_call", fake_check_call)
    bootstrap.ensure_beads(tmp_path)
    assert called["init"] is False  # already initialized → bd init not run
