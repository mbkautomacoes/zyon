"""Tests for webhook payload parsing with media — MBKCHAT format."""
import os
import sys
from unittest.mock import patch


def _import_ws():
    sys.modules.pop("whatsapp_agent.webhook_server", None)
    from whatsapp_agent import webhook_server
    return webhook_server


# Helper para montar payload MBKCHAT
def _payload(info_overrides=None, msg_overrides=None):
    info = {
        "ID": "M1",
        "IsFromMe": False,
        "PushName": "Geo",
        "Chat": "5511999999999@s.whatsapp.net",
        "Sender": "5511999999999@s.whatsapp.net",
        "Type": "text",
        "Timestamp": "2025-01-01T00:00:00Z",
    }
    msg_block = {"conversation": "ola"}
    if info_overrides:
        info.update(info_overrides)
    if msg_overrides:
        msg_block = msg_overrides
    return {
        "type": "Message",
        "token": "tok1",
        "event": {
            "Info": info,
            "Message": msg_block,
        },
    }


def test_text_unchanged(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    pl = _payload()
    msg = handler._parse(pl, session="1")
    assert msg is not None
    assert msg["text"] == "ola"
    assert msg.get("media_path") is None
    assert msg.get("media_type") is None


def test_image_decoded_from_webhook_base64(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    import base64
    b64 = "data:image/jpeg;base64," + base64.b64encode(b"JPEGDATA").decode()
    pl = _payload(
        info_overrides={"ID": "IMG1", "Type": "image"},
        msg_overrides={
            "imageMessage": {
                "base64": b64,
                "mimeType": "image/jpeg",
                "caption": "veja isso",
            }
        },
    )
    msg = handler._parse(pl, session="1")
    assert msg is not None
    assert msg["media_type"] == "imageMessage"
    assert msg["media_path"] is not None
    assert msg["media_path"].endswith("IMG1.jpg")
    assert msg["text"] == "veja isso"


def test_audio_placeholder_no_transcribe(fake_config, tmp_workdir):
    """Webhook only saves audio. Transcription is done by Claude on demand."""
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    import base64
    b64 = "data:audio/ogg;base64," + base64.b64encode(b"AUDIODATA").decode()
    pl = _payload(
        info_overrides={"ID": "AUD1", "Type": "audio"},
        msg_overrides={
            "audioMessage": {
                "base64": b64,
                "mimeType": "audio/ogg; codecs=opus",
            }
        },
    )
    msg = handler._parse(pl, session="1")
    assert msg is not None
    assert msg["media_type"] == "audioMessage"
    assert msg["media_path"] is not None
    assert msg["media_path"].endswith("AUD1.ogg")
    assert msg["text"] == "[audio]"


def test_image_without_caption_uses_placeholder(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    import base64
    b64 = "data:image/png;base64," + base64.b64encode(b"PNGDATA").decode()
    pl = _payload(
        info_overrides={"ID": "IMG2", "Type": "image"},
        msg_overrides={
            "imageMessage": {
                "base64": b64,
                "mimeType": "image/png",
            }
        },
    )
    msg = handler._parse(pl, session="1")
    assert msg is not None
    assert msg["text"] == "[image]"
    assert msg["media_type"] == "imageMessage"


def test_non_message_event_ignored(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "type": "Connected",
        "token": "tok1",
        "event": {},
    }
    msg = handler._parse(payload, session="1")
    assert msg is None


def test_group_message_ignored(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    pl = _payload(
        info_overrides={
            "ID": "G1",
            "Chat": "5511888888888-123456@g.us",
            "Sender": "5511999999999@s.whatsapp.net",
        },
        msg_overrides={"conversation": "ola grupo"},
    )
    msg = handler._parse(pl, session="1")
    assert msg is None


def test_self_chat_from_me_accepted(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    pl = _payload(
        info_overrides={
            "ID": "SELF1",
            "IsFromMe": True,
        },
        msg_overrides={"conversation": "self msg"},
    )
    msg = handler._parse(pl, session="1")
    assert msg is not None
    assert msg["text"] == "self msg"
    assert msg["fromMe"] is True
