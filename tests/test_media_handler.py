"""Tests for media_handler."""
import base64
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("whatsapp_agent.media_handler", None)
    from whatsapp_agent import media_handler
    return media_handler


def test_ext_for_mime(fake_config):
    mh = _import()
    assert mh.ext_for_mime("audio/ogg; codecs=opus") == "ogg"
    assert mh.ext_for_mime("image/jpeg") == "jpg"
    assert mh.ext_for_mime("image/png") == "png"
    assert mh.ext_for_mime("video/mp4") == "mp4"
    assert mh.ext_for_mime("application/octet-stream") == "bin"


def test_strip_data_uri(fake_config):
    mh = _import()
    raw = base64.b64encode(b"HELLO").decode()
    uri = f"data:audio/ogg; codecs=opus;base64,{raw}"
    decoded = mh.decode_data_uri(uri)
    assert decoded == b"HELLO"


def test_decode_data_uri_pure_base64_fallback(fake_config):
    mh = _import()
    raw = base64.b64encode(b"WORLD").decode()
    decoded = mh.decode_data_uri(raw)
    assert decoded == b"WORLD"


def test_save_media_writes_file(fake_config, tmp_workdir):
    mh = _import()
    path = mh.save_media(session="1", msg_id="ABC123", raw=b"AUDIOPAYLOAD", mimetype="audio/ogg; codecs=opus")

    assert path is not None
    assert os.path.exists(path)
    assert path.endswith("ABC123.ogg")
    assert "session1" in path.replace("\\", "/")
    with open(path, "rb") as f:
        assert f.read() == b"AUDIOPAYLOAD"


def test_download_media_writes_file(fake_config, tmp_workdir):
    mh = _import()

    body = base64.b64encode(b"AUDIOPAYLOAD").decode()
    response = '{"success": true, "data": {"base64": "data:audio/ogg;base64,' + body + '"}}'

    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = mh.download_media(
            session="1",
            msg_id="ABC123",
            message_keys={
                "mediaKey": "MK==",
                "directPath": "/v/x.enc",
                "url": "https://x/x.enc",
                "mimetype": "audio/ogg; codecs=opus",
                "messageType": "audioMessage",
            },
        )

    assert path is not None
    assert os.path.exists(path)
    assert path.endswith("ABC123.ogg")
    with open(path, "rb") as f:
        assert f.read() == b"AUDIOPAYLOAD"


def test_download_media_returns_none_on_api_error(fake_config, tmp_workdir):
    mh = _import()

    response = '{"success": false, "error": "media not found"}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = mh.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "image/jpeg", "messageType": "imageMessage",
            },
        )
    assert path is None


def test_download_media_handles_malformed_base64(fake_config, tmp_workdir):
    mh = _import()
    response = '{"success": true, "data": {"base64": "data:audio/ogg;base64,not!!valid%%base64"}}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("whatsapp_agent.media_handler.subprocess.run", return_value=fake_proc):
        path = mh.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "audio/ogg; codecs=opus", "messageType": "audioMessage",
            },
        )
    assert path is None


def test_save_media_sanitises_session(fake_config, tmp_workdir):
    """Path traversal in session must be neutralised."""
    mh = _import()
    path = mh.save_media(session="../../evil", msg_id="X", raw=b"PAYLOAD", mimetype="audio/ogg")

    assert path is not None
    norm = path.replace("\\", "/")
    assert ".." not in norm
    assert "evil" in norm
    assert norm.startswith("media/") or "/media/session" in norm


def test_extract_media_base64_from_webhook(fake_config):
    mh = _import()
    payload = {
        "message": {
            "imageMessage": {
                "base64": "data:image/jpeg;base64,/9j/4AAQ",
                "mimeType": "image/jpeg",
                "caption": "foto",
            }
        }
    }
    b64 = mh.extract_media_base64(payload, "imageMessage")
    assert b64 == "data:image/jpeg;base64,/9j/4AAQ"


def test_extract_media_base64_returns_none_when_missing(fake_config):
    mh = _import()
    payload = {"message": {"imageMessage": {"mimeType": "image/jpeg"}}}
    b64 = mh.extract_media_base64(payload, "imageMessage")
    assert b64 is None


def test_detect_message_type_from_message_block(fake_config):
    mh = _import()
    assert mh.detect_message_type({"message": {"audioMessage": {}}}) == "audioMessage"
    assert mh.detect_message_type({"message": {"imageMessage": {}}}) == "imageMessage"
    assert mh.detect_message_type({"message": {"conversation": "texto"}}) is None
