"""Tests for transcribe."""
import sys
from unittest.mock import patch, MagicMock


def _import_transcribe(openai_key=""):
    """Set OPENAI_API_KEY on config, then fresh-import transcribe so the
    module-level `from config import OPENAI_API_KEY` picks up the value."""
    import config
    config.OPENAI_API_KEY = openai_key
    sys.modules.pop("whatsapp_agent.transcribe", None)
    import whatsapp_agent
    if hasattr(whatsapp_agent, "transcribe"):
        delattr(whatsapp_agent, "transcribe")
    from whatsapp_agent import transcribe
    return transcribe


def test_no_key_returns_marker(fake_config):
    transcribe = _import_transcribe(openai_key="")
    text = transcribe.transcribe_audio("/fake.ogg")
    assert text.startswith("[audio - transcricao desativada")


def test_returns_text_on_success(fake_config, tmp_workdir):
    transcribe = _import_transcribe(openai_key="sk-test")
    p = tmp_workdir / "a.ogg"
    p.write_bytes(b"x")
    proc = MagicMock(stdout='{"text": "ola mundo"}', stderr="", returncode=0)
    with patch("whatsapp_agent.transcribe.subprocess.run", return_value=proc):
        text = transcribe.transcribe_audio(str(p))
    assert text == "ola mundo"


def test_returns_marker_on_api_error(fake_config, tmp_workdir):
    transcribe = _import_transcribe(openai_key="sk-test")
    p = tmp_workdir / "a.ogg"
    p.write_bytes(b"x")
    proc = MagicMock(stdout='{"error": {"message": "invalid"}}', stderr="", returncode=0)
    with patch("whatsapp_agent.transcribe.subprocess.run", return_value=proc):
        text = transcribe.transcribe_audio(str(p))
    assert text.startswith("[audio - erro")


def test_returns_marker_when_file_missing(fake_config):
    transcribe = _import_transcribe(openai_key="sk-test")
    text = transcribe.transcribe_audio("/nonexistent.ogg")
    assert "nao encontrado" in text


def test_returns_marker_on_curl_failure(fake_config, tmp_workdir):
    transcribe = _import_transcribe(openai_key="sk-test")
    p = tmp_workdir / "a.ogg"
    p.write_bytes(b"x")
    proc = MagicMock(stdout="", stderr="curl: (6) Could not resolve host", returncode=6)
    with patch("whatsapp_agent.transcribe.subprocess.run", return_value=proc):
        text = transcribe.transcribe_audio(str(p))
    assert text.startswith("[audio - erro de rede")
    assert "Could not resolve" in text
