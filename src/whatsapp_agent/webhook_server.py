from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import re

PORT = 3020

from config import SESSIONS
from whatsapp_agent import media_handler


def messages_file(session: str) -> str:
    return f"messages_session{session}.jsonl"


def allowed_phone(session: str) -> str:
    return SESSIONS.get(session, SESSIONS["1"])["phone"]


def _extract_phone_from_jid(jid: str) -> str:
    """Extract digits-only phone from a JID like '5511922442053@s.whatsapp.net' or '123:2@lid'."""
    if not jid:
        return ""
    # Remove :N suffix (e.g. "556296414177:2@s.whatsapp.net")
    jid = re.sub(r":\d+@", "@", jid)
    return jid.replace("@s.whatsapp.net", "").replace("@lid", "")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/healthz":
            try:
                import config as _cfg
                sessions = list(_cfg.SESSIONS.keys())
            except Exception:
                sessions = list(SESSIONS.keys())
            body = json.dumps({
                "status": "ok",
                "sessions": sessions,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"not found")

    def do_POST(self):
        qs = parse_qs(urlparse(self.path).query)
        session = qs.get("session", ["1"])[0]

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        with open("raw_debug.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        msg = self._parse(data, session)
        if msg:
            msg["session"] = session
            fname = messages_file(session)
            with open(fname, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            print(f"MSG|s{session}|{msg['from']}|{msg['name']}|{msg['text']}", flush=True)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def _parse(self, data, session: str = "1"):
        try:
            # MBKCHAT format: {"type": "Message", "token": "...", "event": {"Info": {...}, "Message": {...}}}
            if data.get("type") != "Message":
                return None

            event = data.get("event", {}) or {}
            info = event.get("Info", {}) or {}
            msg_block = event.get("Message", {}) or {}

            msg_id = info.get("ID", "")
            from_me = info.get("IsFromMe", False)
            push_name = info.get("PushName", "")
            msg_type = info.get("Type", "")  # "text", "image", "audio", etc.

            # Extract phone from various JID fields
            chat_jid = info.get("Chat", "")
            sender_jid = info.get("Sender", "")
            recipient_alt = info.get("RecipientAlt", "")
            sender_alt = info.get("SenderAlt", "")

            sess_phone = allowed_phone(session)

            # Check if this message involves the configured phone
            phones_involved = set()
            for jid in [chat_jid, sender_jid, recipient_alt, sender_alt]:
                p = _extract_phone_from_jid(jid)
                if p:
                    phones_involved.add(p)

            if sess_phone not in phones_involved:
                return None

            # Determine the "from" phone and JID
            if from_me:
                # Message sent by us (self-chat) - use our own phone
                phone = sess_phone
                jid = sender_jid or chat_jid
            else:
                # Incoming message from someone else
                if sender_alt:
                    phone = _extract_phone_from_jid(sender_alt)
                    jid = sender_alt
                elif sender_jid:
                    phone = _extract_phone_from_jid(sender_jid)
                    jid = sender_jid
                else:
                    phone = _extract_phone_from_jid(chat_jid)
                    jid = chat_jid

            # Group/newsletter filter — check all JIDs
            if any("@g.us" in j or "@newsletter" in j
                   for j in [chat_jid, sender_jid, jid] if j):
                return None

            # Detect media vs text
            text = None
            media_path = None
            message_type = None

            if msg_type == "image" or "imageMessage" in msg_block:
                message_type = "imageMessage"
                inner = msg_block.get("imageMessage", {}) or {}
                b64 = inner.get("base64", "")
                mimetype = inner.get("mimeType", "") or inner.get("mimetype", "")
                if b64:
                    try:
                        raw = media_handler.decode_data_uri(b64)
                        if raw:
                            media_path = media_handler.save_media(session, msg_id, raw, mimetype)
                    except Exception:
                        pass
                caption = inner.get("caption")
                text = caption or "[image]"

            elif msg_type == "audio" or "audioMessage" in msg_block:
                message_type = "audioMessage"
                inner = msg_block.get("audioMessage", {}) or {}
                b64 = inner.get("base64", "")
                mimetype = inner.get("mimeType", "") or inner.get("mimetype", "")
                if b64:
                    try:
                        raw = media_handler.decode_data_uri(b64)
                        if raw:
                            media_path = media_handler.save_media(session, msg_id, raw, mimetype)
                    except Exception:
                        pass
                text = "[audio]"

            elif msg_type == "video" or "videoMessage" in msg_block:
                message_type = "videoMessage"
                inner = msg_block.get("videoMessage", {}) or {}
                b64 = inner.get("base64", "")
                mimetype = inner.get("mimeType", "") or inner.get("mimetype", "")
                if b64:
                    try:
                        raw = media_handler.decode_data_uri(b64)
                        if raw:
                            media_path = media_handler.save_media(session, msg_id, raw, mimetype)
                    except Exception:
                        pass
                caption = inner.get("caption")
                text = caption or "[video]"

            else:
                # Plain text
                text = (
                    msg_block.get("conversation")
                    or msg_block.get("extendedTextMessage", {}).get("text")
                )
                # Handle protocolMessage (edited messages, etc.)
                if not text:
                    proto = msg_block.get("protocolMessage", {}) or {}
                    edited = proto.get("editedMessage", {}) or {}
                    text = edited.get("extendedTextMessage", {}).get("text")
                if not text:
                    text = "[midia]"

            # Loop guard: filter out messages containing our own signature
            if text and "*Claude Code*" in text:
                return None

            # Parse timestamp
            ts_raw = info.get("Timestamp", "")
            ts = 0
            if ts_raw:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts_raw)
                    ts = int(dt.timestamp())
                except Exception:
                    ts = 0

            return {
                "id":         msg_id,
                "from":       phone,
                "jid":        jid,
                "name":       push_name,
                "text":       text,
                "ts":         ts,
                "fromMe":     from_me,
                "media_type": message_type,
                "media_path": media_path,
            }
        except Exception as e:
            print(f"PARSE_ERROR: {e}", flush=True)
            return None

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"[webhook] listening on :{PORT}", flush=True)
    print(f"[webhook] use ?session=1, ?session=2 etc. na URL do webhook", flush=True)
    HTTPServer(("0.0.0.0", PORT), WebhookHandler).serve_forever()
