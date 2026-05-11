"""
Download de media (audio/imagem/video) via API WuzAPI / MBKCHAT.

WuzAPI envia media como base64 diretamente no payload do webhook (campo
data.message.{imageMessage,audioMessage,videoMessage}.base64).
Quando o base64 nao esta presente, usamos o endpoint /chat/downloadimage.

Layout local: media/sessionN/<msg_id>.<ext>
"""
import base64
import json
import os
import subprocess
from typing import Optional

from config import SESSIONS, API_HOST


MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png":  "png",
    "image/webp": "webp",
    "image/gif":  "gif",
    "audio/ogg":  "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4":  "m4a",
    "audio/wav":  "wav",
    "video/mp4":  "mp4",
    "video/webm": "webm",
}


def ext_for_mime(mimetype: str) -> str:
    base = (mimetype or "").split(";")[0].strip().lower()
    return MIME_EXT.get(base, "bin")


def detect_message_type(payload: dict) -> Optional[str]:
    """Returns 'audioMessage' / 'imageMessage' / 'videoMessage' or None."""
    mt = payload.get("messageType", "")
    if mt in ("audioMessage", "imageMessage", "videoMessage"):
        return mt
    msg = payload.get("message", {}) or {}
    for k in ("audioMessage", "imageMessage", "videoMessage"):
        if k in msg:
            return k
    return None


def extract_media_base64(payload: dict, message_type: str) -> Optional[str]:
    """Extract base64 data from a WuzAPI webhook payload. Returns None if not present."""
    msg = payload.get("message", {}) or {}
    inner = msg.get(message_type, {}) or {}
    b64 = inner.get("base64", "")
    if b64:
        return b64
    return None


def extract_media_mimetype(payload: dict, message_type: str) -> str:
    """Extract mimetype from a WuzAPI webhook payload."""
    msg = payload.get("message", {}) or {}
    inner = msg.get(message_type, {}) or {}
    return inner.get("mimeType", "") or inner.get("mimetype", "")


def decode_data_uri(s: str) -> bytes:
    """Strips 'data:MIME;base64,' prefix if present, decodes base64."""
    if not s:
        return b""
    if s.startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    return base64.b64decode(s)


def save_media(session: str, msg_id: str, raw: bytes, mimetype: str) -> Optional[str]:
    """Save raw bytes to media/sessionN/<msg_id>.<ext>. Returns local path."""
    ext = ext_for_mime(mimetype)
    safe_session = "".join(c for c in str(session) if c.isalnum())
    out_dir = os.path.join("media", f"session{safe_session}")
    os.makedirs(out_dir, exist_ok=True)
    safe_id = "".join(c for c in msg_id if c.isalnum() or c in "-_")
    out_path = os.path.join(out_dir, f"{safe_id}.{ext}")
    with open(out_path, "wb") as f:
        f.write(raw)
    return out_path


def download_media(session: str, msg_id: str, message_keys: dict) -> Optional[str]:
    """
    Calls WuzAPI /chat/downloadimage endpoint, saves bytes to media/sessionN/<msg_id>.<ext>.
    Returns local path on success, None on failure.
    """
    cfg = SESSIONS.get(session, SESSIONS.get("1"))
    if not cfg:
        return None

    endpoint = f"{API_HOST}/chat/downloadimage"
    payload = json.dumps({"messageKeys": message_keys})

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", endpoint,
                "-H", "accept: */*",
                "-H", f"token: {cfg['token']}",
                "-H", "Content-Type: application/json",
                "-d", payload,
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except Exception as e:
        print(f"DOWNLOAD_ERROR: {e}", flush=True)
        return None

    try:
        data = json.loads(result.stdout)
    except Exception:
        print(f"DOWNLOAD_PARSE_ERROR: {result.stdout[:200]}", flush=True)
        return None

    if not data.get("success"):
        print(f"DOWNLOAD_API_ERROR: {data.get('error')}", flush=True)
        return None

    try:
        raw = decode_data_uri(data.get("data", {}).get("base64", ""))
    except Exception:
        print(f"DOWNLOAD_DECODE_ERROR: bad base64 in response", flush=True)
        return None
    if not raw:
        return None

    mimetype = message_keys.get("mimetype", "")
    return save_media(session, msg_id, raw, mimetype)
