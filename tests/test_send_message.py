"""Tests for send_message routing."""
import json
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("whatsapp_agent.send_message", None)
    from whatsapp_agent import send_message
    return send_message


def test_send_text_uses_text_endpoint(fake_config):
    sm = _import()
    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_text("5511888888888", "ola", "1")

    assert result == {"success": True}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert url.endswith("/chat/send/text")


def test_send_image_posts_correct_payload(fake_config, tmp_workdir):
    sm = _import()
    img = tmp_workdir / "x.jpg"
    img.write_bytes(b"IMGBYTES")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_image("5511888888888", str(img), caption="legenda", session="1")

    assert result == {"success": True}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert "/chat/send/image" in url

    body_idx = captured["args"].index("-d") + 1
    body_raw = captured["args"][body_idx]
    body = json.loads(body_raw)
    assert body["Phone"] == "5511888888888"
    assert body["Image"].startswith("data:image/jpeg;base64,")
    assert "SU1HQllURVM=" in body["Image"]  # base64 of "IMGBYTES"
    assert "legenda" in body["Caption"]


def test_send_image_missing_file_returns_error(fake_config):
    sm = _import()
    result = sm.send_image("5511888888888", "/nonexistent.jpg", session="1")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_send_image_detects_mime_from_extension(fake_config, tmp_workdir):
    sm = _import()
    png = tmp_workdir / "x.png"
    png.write_bytes(b"PNGDATA")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)

    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_image("5511888888888", str(png), session="1")

    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    assert body["Image"].startswith("data:image/png;base64,")


def test_send_image_rejects_oversized_file(fake_config, tmp_workdir, monkeypatch):
    sm = _import()
    big = tmp_workdir / "big.jpg"
    big.write_bytes(b"X" * 1024)

    monkeypatch.setattr(sm, "MAX_IMAGE_BYTES", 100)
    result = sm.send_image("5511888888888", str(big), session="1")
    assert "error" in result
    assert "too large" in result["error"].lower()


def test_send_text_strips_pre_existing_signature(fake_config):
    sm = _import()
    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)
    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "Tudo certo. *Claude Code*", "1")
    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    text = body["Body"]
    assert text.count("*Claude Code*") == 1, f"Signature deve aparecer 1x, veio: {text!r}"
    assert text.startswith("Tudo certo.")


def test_send_text_appends_signature_when_missing(fake_config):
    sm = _import()
    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)
    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "ola", "1")
    body = json.loads(captured["args"][captured["args"].index("-d") + 1])
    text = body["Body"]
    assert text.count("*Claude Code*") == 1


def test_send_text_auth_header_is_token(fake_config):
    sm = _import()
    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"success": true}', stderr="", returncode=0)
    with patch("whatsapp_agent.send_message.subprocess.run", side_effect=fake_run):
        sm.send_text("5511888888888", "test", "1")
    # Check auth header is token: not Authorization: Bearer
    headers = [captured["args"][i+1] for i, a in enumerate(captured["args"]) if a == "-H"]
    assert "token: tok1" in headers
    assert not any("Authorization" in h for h in headers)
