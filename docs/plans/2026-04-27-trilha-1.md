# Trilha 1 Closure: Multi-Session + Multimodal Receive + Image Send

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close Trilha 1 with (1) easy add of new WhatsApp instances, (2) receive image+audio (decrypted via megaAPI), (3) send images, (4) transcribe audio via OpenAI Whisper.

**Architecture:**
- **Multi-session add:** `add_session.py` mutates `config.py` preserving existing sessions, picks next free ID.
- **Receive media:** webhook detects `messageType` top-level field. Calls megaAPI `/rest/instance/downloadMediaMessage/<instance>` with `{mediaKey, directPath, url, mimetype, messageType}`. Response is `{error, message, data}` where `data` is a **data URI** (`data:MIME;base64,XXX`). Strip prefix, decode, save to `media/sessionN/<msg_id>.<ext>`. Webhook writes `media_path`/`media_type` to JSONL but does **NOT** auto-transcribe — Claude calls `transcribe.py` when desired.
- **Transcribe audio:** `transcribe.py` posts ogg/opus to OpenAI Whisper (`/v1/audio/transcriptions`). Single dependency. Optional — works without if `OPENAI_API_KEY` empty.
- **Send image:** `send_message.py` gains `send_image()` using megaAPI `/sendMediaMessage` endpoint (exact shape verified in Task 8 against megaAPI swagger before implementation).

**Tech Stack:**
- Python 3.8+ stdlib
- `curl` (Cloudflare-proof HTTP)
- OpenAI Whisper API (single optional dependency)
- megaAPI: `/rest/instance/downloadMediaMessage/{instance}` (verified working) + `/sendMediaMessage` (to verify in Task 8)

**Out of scope:**
- Send audio / TTS (cut per user)
- Video transcription/analysis (downloaded only, Claude responds "videos não suportados")
- Auto-transcription in webhook (deferred — keeps webhook stateless and cheap)
- Trilha 2 (VPS, Cloudflare Tunnel)

**Verified findings (recon Apr 27 2026):**
- megaAPI delivers media as encrypted `.enc` URLs — DO NOT curl directly.
- `messageType` field at top of payload: `audioMessage` / `imageMessage` / `videoMessage` — clean routing.
- `audioMessage` mimetype: `audio/ogg; codecs=opus`, `ptt: true` for voice notes — Whisper accepts ogg natively.
- `imageMessage` includes `jpegThumbnail` (small base64 preview) — could be used as fallback if download fails (not in scope here).
- Download endpoint payload key is `messageKeys` (plural).
- Download response shape: `{error: bool, message: str, data: "data:<mime>;base64,<b64>"}` — must split on `,` to extract pure base64.
- Group filtering already works via existing `@g.us` check.

---

## File Structure

**New:**
- `add_session.py` — append session to config.py
- `media_handler.py` — download via megaAPI decrypt endpoint, save to media/sessionN/
- `transcribe.py` — Whisper wrapper
- `media/` — runtime storage (gitignored)
- `tests/__init__.py`, `tests/conftest.py`
- `tests/test_add_session.py`, `tests/test_media_handler.py`, `tests/test_transcribe.py`,
  `tests/test_webhook_parser.py`, `tests/test_send_message.py`, `tests/test_setup_config.py`

**Modified:**
- `config.example.py` — add `OPENAI_API_KEY`
- `setup_config.py` — prompt for OPENAI_API_KEY (optional)
- `webhook_server.py:48-84` (`_parse`) — detect+download media, write media_path
- `send_message.py` — add `send_image()`, CLI flag `--type image`
- `doctor.py` — validate OPENAI_API_KEY
- `.gitignore` — add `media/`
- `CLAUDE_PROMPT.md` — multimodal handling instructions
- `README.md`, `SETUP.md` — multi-session + multimodal docs

---

## Task 1: Test scaffold + .gitignore

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `tests/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
import sys
import pytest


@pytest.fixture
def tmp_workdir(tmp_path, monkeypatch):
    """Isolated cwd. Repo root on sys.path so production modules import."""
    import os
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def fake_config(tmp_workdir):
    """Write minimal config.py into tmp cwd. Yields the cwd path."""
    cfg = '''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
MEGA_HOST = "https://apibusiness1.megaapi.com.br"
SESSIONS = {
    "1": {
        "instance": "inst1",
        "token":    "tok1",
        "phone":    "5511999999999",
        "lid":      "11111111111111",
    },
}
ALLOWED_PHONE = SESSIONS["1"]["phone"]
ALLOWED_LID   = SESSIONS["1"]["lid"]
MEGA_INSTANCE = SESSIONS["1"]["instance"]
MEGA_TOKEN    = SESSIONS["1"]["token"]
MEGA_BASE_URL = f"{MEGA_HOST}/rest/sendMessage/{MEGA_INSTANCE}"
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")
    sys.path.insert(0, str(tmp_workdir))
    yield tmp_workdir
    sys.path.remove(str(tmp_workdir))
    sys.modules.pop("config", None)
```

- [ ] **Step 3: Append to `.gitignore`**

```
# Media files (downloaded image/audio/video)
media/
```

- [ ] **Step 4: Verify pytest installed**

Run: `python -m pytest --version`
Expected: version printed. If missing: `pip install pytest`

- [ ] **Step 5: Verify discovery**

Run: `python -m pytest tests/ -v`
Expected: `no tests ran` (exit code 5) — confirms collection works.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/conftest.py .gitignore
git commit -m "test: scaffold pytest with shared fixtures + gitignore media/"
```

---

## Task 2: Add OPENAI_API_KEY to config.example.py

**Files:**
- Modify: `config.example.py`

- [ ] **Step 1: Append before `# Defaults derivados`**

```python
# ------------------------------------------------------------
# Multimodal (opcional - deixe em branco para desativar)
# ------------------------------------------------------------
# OpenAI Whisper para transcrever audios recebidos.
# Pegue chave: https://platform.openai.com/api-keys
OPENAI_API_KEY = ""
```

- [ ] **Step 2: Syntax check**

Run: `python -m py_compile config.example.py`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add config.example.py
git commit -m "feat: OPENAI_API_KEY in config template"
```

---

## Task 3: setup_config.py prompts for OpenAI key

**Files:**
- Modify: `setup_config.py`
- Create: `tests/test_setup_config.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for setup_config wizard."""
from unittest.mock import patch


def test_writes_config_with_openai_key(fake_config, tmp_workdir):
    # delete the seeded config so wizard writes fresh
    (tmp_workdir / "config.py").unlink()

    import setup_config

    inputs = iter([
        "meutoken",
        "megabusiness-test",
        "abc123",
        "5511999999999",
        "sk-test123",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'meutoken'" in content
    assert "'sk-test123'" in content
    assert "OPENAI_API_KEY" in content


def test_blank_openai_key_allowed(fake_config, tmp_workdir):
    (tmp_workdir / "config.py").unlink()
    import setup_config

    inputs = iter([
        "meutoken",
        "megabusiness-test",
        "abc123",
        "5511999999999",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY = ''" in content
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_setup_config.py -v`
Expected: FAIL — current `setup_config.py` does not prompt for OPENAI_API_KEY.

- [ ] **Step 3: Modify `setup_config.py`** — in `main()`, after the phone validation block (`if not phone: ... return 1`), insert:

```python
    print("")
    print("--- Multimodal (opcional) ---")
    openai_key = ask("OPENAI_API_KEY (transcricao de audio via Whisper, deixe vazio para pular)",
                     default="", required=False)
```

Update the `cfg` dict:

```python
    cfg = {
        "cmd_token": cmd_token,
        "signature": "*Claude Code*",
        "mega_host": "https://apibusiness1.megaapi.com.br",
        "instance":  instance,
        "token":     token,
        "phone":     phone,
        "lid":       "",
        "openai_key": openai_key,
    }
```

Update `write_config()` template — insert before the `ALLOWED_PHONE` line:

```python
OPENAI_API_KEY = {cfg["openai_key"]!r}

```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest tests/test_setup_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add setup_config.py tests/test_setup_config.py
git commit -m "feat(setup): prompt for OPENAI_API_KEY"
```

---

## Task 4: add_session.py wizard

**Files:**
- Create: `add_session.py`
- Create: `tests/test_add_session.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for add_session wizard."""
from unittest.mock import patch


def _seed(tmp_workdir, sessions_block):
    cfg = f'''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
MEGA_HOST = "https://apibusiness1.megaapi.com.br"
SESSIONS = {{
{sessions_block}
}}
ALLOWED_PHONE = "111"
ALLOWED_LID = ""
MEGA_INSTANCE = "i1"
MEGA_TOKEN = "t1"
MEGA_BASE_URL = ""
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")


def test_appends_second_session(fake_config, tmp_workdir):
    _seed(tmp_workdir, '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},')
    import add_session

    inputs = iter(["megabusiness-second", "tok2", "5511888888888"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"2":' in content
    assert "megabusiness-second" in content
    assert "5511888888888" in content
    assert '"1":' in content  # original preserved


def test_picks_next_free_id(fake_config, tmp_workdir):
    _seed(tmp_workdir,
          '    "1": {"instance": "i1", "token": "t1", "phone": "111", "lid": ""},\n'
          '    "2": {"instance": "i2", "token": "t2", "phone": "222", "lid": ""},')
    import add_session

    inputs = iter(["i3", "t3", "5511777777777"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"3":' in content
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_add_session.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `add_session.py`**

```python
"""
Adiciona uma nova sessao (instancia megaAPI) ao config.py existente.

Usage: python add_session.py

Preserva sessoes existentes. Atribui o proximo ID livre.
"""
import os
import re
import sys


CONFIG_PATH = "config.py"


def ask(label: str, default: str = "", required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"  {label}{suffix}: ").strip()
        if not val:
            val = default
        if val or not required:
            return val
        print("    -> obrigatorio.")


def normalize_phone(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def next_session_id(existing_ids):
    n = 1
    while str(n) in existing_ids:
        n += 1
    return str(n)


def append_session(instance: str, token: str, phone: str) -> str:
    """Mutates config.py in-place. Returns new session id."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        content = f.read()

    ns: dict = {}
    exec(content, ns)
    sessions = ns.get("SESSIONS", {})
    new_id = next_session_id(sessions.keys())

    new_block = (
        f'    "{new_id}": {{\n'
        f'        "instance": {instance!r},\n'
        f'        "token":    {token!r},\n'
        f'        "phone":    {phone!r},\n'
        f'        "lid":      "",\n'
        f'    }},\n'
    )

    m = re.search(r"SESSIONS\s*=\s*\{", content)
    if not m:
        raise RuntimeError("Nao encontrei 'SESSIONS = {' em config.py")
    start = m.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        c = content[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise RuntimeError("SESSIONS dict mal formado em config.py")
    close_brace = i - 1

    new_content = content[:close_brace] + new_block + content[close_brace:]
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return new_id


def main() -> int:
    if not os.path.exists(CONFIG_PATH):
        print("  ERRO: config.py nao existe. Rode setup_config.py primeiro.")
        return 1

    print("")
    print("=" * 60)
    print("Adicionar nova sessao WhatsApp")
    print("=" * 60)
    print("")
    instance = ask("Nome da instancia megaAPI (ex: megabusiness-segundo)")
    token    = ask("Token da instancia")
    phone    = normalize_phone(ask("Numero WhatsApp (5511999999999)"))
    if not phone:
        print("  ERRO: numero invalido.")
        return 1

    try:
        new_id = append_session(instance, token, phone)
    except Exception as e:
        print(f"  ERRO: {e}")
        return 1

    print("")
    print(f"  OK: sessao '{new_id}' adicionada ao config.py")
    print("")
    print("Proximos passos:")
    print(f"  1. Configure webhook na nova instancia megaAPI:")
    print(f"     <SUA_URL_NGROK>/?session={new_id}")
    print(f"  2. Mande 1 mensagem WhatsApp pra voce mesmo")
    print(f"  3. Rode:  python discover_lid.py {new_id}")
    print(f"  4. Em outra sessao Claude Code:  python monitor.py {new_id}")
    print("")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Cancelado.")
        sys.exit(130)
```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest tests/test_add_session.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add add_session.py tests/test_add_session.py
git commit -m "feat: add_session.py wizard"
```

---

## Task 5: media_handler.py — download via megaAPI decrypt endpoint

**Files:**
- Create: `media_handler.py`
- Create: `tests/test_media_handler.py`

This task is grounded in the verified payload shape from recon. Endpoint:

```
POST {MEGA_HOST}/rest/instance/downloadMediaMessage/{instance}
Headers: Authorization: Bearer <token>
Body: {"messageKeys": {"mediaKey":..., "directPath":..., "url":..., "mimetype":..., "messageType":...}}
Response: {"error": bool, "message": str, "data": "data:<mime>;base64,<b64>"}
```

- [ ] **Step 1: Write failing test**

```python
"""Tests for media_handler."""
import base64
import os
from unittest.mock import patch, MagicMock


def test_extract_message_keys_from_audio(fake_config):
    import media_handler
    msg_block = {
        "audioMessage": {
            "url": "https://x/file.enc",
            "mimetype": "audio/ogg; codecs=opus",
            "mediaKey": "MK==",
            "directPath": "/v/path.enc",
        }
    }
    keys = media_handler.extract_message_keys(msg_block, "audioMessage")
    assert keys == {
        "mediaKey": "MK==",
        "directPath": "/v/path.enc",
        "url": "https://x/file.enc",
        "mimetype": "audio/ogg; codecs=opus",
        "messageType": "audioMessage",
    }


def test_ext_for_mime():
    import media_handler
    assert media_handler.ext_for_mime("audio/ogg; codecs=opus") == "ogg"
    assert media_handler.ext_for_mime("image/jpeg") == "jpg"
    assert media_handler.ext_for_mime("image/png") == "png"
    assert media_handler.ext_for_mime("video/mp4") == "mp4"
    assert media_handler.ext_for_mime("application/octet-stream") == "bin"


def test_strip_data_uri():
    import media_handler
    raw = base64.b64encode(b"HELLO").decode()
    uri = f"data:audio/ogg; codecs=opus;base64,{raw}"
    decoded = media_handler.decode_data_uri(uri)
    assert decoded == b"HELLO"


def test_decode_data_uri_pure_base64_fallback():
    import media_handler
    raw = base64.b64encode(b"WORLD").decode()
    # some servers may omit the data: prefix
    decoded = media_handler.decode_data_uri(raw)
    assert decoded == b"WORLD"


def test_download_media_writes_file(fake_config, tmp_workdir):
    import media_handler

    body = base64.b64encode(b"AUDIOPAYLOAD").decode()
    response = '{"error": false, "message": "ok", "data": "data:audio/ogg;base64,' + body + '"}'

    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
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
    assert "session1" in path.replace("\\", "/")
    with open(path, "rb") as f:
        assert f.read() == b"AUDIOPAYLOAD"


def test_download_media_returns_none_on_api_error(fake_config, tmp_workdir):
    import media_handler

    response = '{"error": true, "message": "media not found"}'
    fake_proc = MagicMock(stdout=response, stderr="", returncode=0)
    with patch("media_handler.subprocess.run", return_value=fake_proc):
        path = media_handler.download_media(
            session="1",
            msg_id="X",
            message_keys={
                "mediaKey": "x", "directPath": "x", "url": "x",
                "mimetype": "image/jpeg", "messageType": "imageMessage",
            },
        )
    assert path is None
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_media_handler.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `media_handler.py`**

```python
"""
Download de media (audio/imagem/video) via endpoint decrypt da megaAPI.

WhatsApp criptografa media end-to-end. URL .enc nao serve direto.
megaAPI tem endpoint que decripta server-side e retorna base64.

Endpoint: POST /rest/instance/downloadMediaMessage/{instance}
Body: {"messageKeys": {mediaKey, directPath, url, mimetype, messageType}}
Resp: {"error": bool, "message": str, "data": "data:MIME;base64,XXX"}

Layout local: media/sessionN/<msg_id>.<ext>
"""
import base64
import json
import os
import subprocess
from typing import Optional

from config import SESSIONS, MEGA_HOST


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
    # fallback: inspect message block
    msg = payload.get("message", {}) or {}
    for k in ("audioMessage", "imageMessage", "videoMessage"):
        if k in msg:
            return k
    return None


def extract_message_keys(msg_block: dict, message_type: str) -> Optional[dict]:
    """Builds the messageKeys body for downloadMediaMessage. Returns None if missing fields."""
    inner = msg_block.get(message_type) or {}
    required = ("mediaKey", "directPath", "url", "mimetype")
    if not all(inner.get(k) for k in required):
        return None
    return {
        "mediaKey":    inner["mediaKey"],
        "directPath":  inner["directPath"],
        "url":         inner["url"],
        "mimetype":    inner["mimetype"],
        "messageType": message_type,
    }


def decode_data_uri(s: str) -> bytes:
    """Strips 'data:MIME;base64,' prefix if present, decodes base64."""
    if not s:
        return b""
    if s.startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    return base64.b64decode(s)


def download_media(session: str, msg_id: str, message_keys: dict) -> Optional[str]:
    """
    Calls megaAPI decrypt endpoint, saves bytes to media/sessionN/<msg_id>.<ext>.
    Returns local path on success, None on failure.
    """
    cfg = SESSIONS.get(session, SESSIONS.get("1"))
    if not cfg:
        return None

    endpoint = f"{MEGA_HOST}/rest/instance/downloadMediaMessage/{cfg['instance']}"
    payload = json.dumps({"messageKeys": message_keys})

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", endpoint,
                "-H", "accept: */*",
                "-H", f"Authorization: Bearer {cfg['token']}",
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

    if data.get("error"):
        print(f"DOWNLOAD_API_ERROR: {data.get('message')}", flush=True)
        return None

    raw = decode_data_uri(data.get("data", ""))
    if not raw:
        return None

    ext = ext_for_mime(message_keys.get("mimetype", ""))
    out_dir = os.path.join("media", f"session{session}")
    os.makedirs(out_dir, exist_ok=True)
    safe_id = "".join(c for c in msg_id if c.isalnum() or c in "-_")
    out_path = os.path.join(out_dir, f"{safe_id}.{ext}")
    with open(out_path, "wb") as f:
        f.write(raw)
    return out_path
```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest tests/test_media_handler.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Live integration check (real megaAPI)**

Run from project root with the audio mediaKey from earlier recon:

```bash
python -c "
from media_handler import download_media
keys = {
  'mediaKey':    'Ke/yqP4CLKpt1OtbircqW+n9rCht7OWoxMPh8zWzpwg=',
  'directPath':  '/v/t62.7117-24/533249428_982496110886995_5051922327473589173_n.enc?ccb=11-4&oh=01_Q5Aa4QEttwyhWtGJb6M3iaR4jYAUfgfm_1SXCO7xso_fDhRlIw&oe=6A174E4E&_nc_sid=5e03e0',
  'url':         'https://mmg.whatsapp.net/v/t62.7117-24/533249428_982496110886995_5051922327473589173_n.enc?ccb=11-4&oh=01_Q5Aa4QEttwyhWtGJb6M3iaR4jYAUfgfm_1SXCO7xso_fDhRlIw&oe=6A174E4E&_nc_sid=5e03e0',
  'mimetype':    'audio/ogg; codecs=opus',
  'messageType': 'audioMessage',
}
p = download_media('1', 'TEST_AUDIO_DECRYPT', keys)
print('saved:', p)
import os
print('size:', os.path.getsize(p) if p else 'NONE')
"
```

Expected output:
```
saved: media/session1/TEST_AUDIO_DECRYPT.ogg
size: 14112
```
(Size 14112 matches `fileLength` from recon. If the media expired meanwhile, send a fresh audio first and grab new keys from `raw_debug.jsonl`.)

- [ ] **Step 6: Commit**

```bash
git add media_handler.py tests/test_media_handler.py
git commit -m "feat: media_handler downloads via megaAPI decrypt endpoint"
```

---

## Task 6: transcribe.py — OpenAI Whisper

**Files:**
- Create: `transcribe.py`
- Create: `tests/test_transcribe.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for transcribe."""
from unittest.mock import patch, MagicMock


def test_no_key_returns_marker(fake_config):
    import config
    config.OPENAI_API_KEY = ""
    import transcribe
    text = transcribe.transcribe_audio("/fake.ogg")
    assert text.startswith("[audio - transcricao desativada")


def test_returns_text_on_success(fake_config, tmp_workdir):
    import config
    config.OPENAI_API_KEY = "sk-test"
    import transcribe

    p = tmp_workdir / "a.ogg"
    p.write_bytes(b"x")

    proc = MagicMock(stdout='{"text": "ola mundo"}', stderr="", returncode=0)
    with patch("transcribe.subprocess.run", return_value=proc):
        text = transcribe.transcribe_audio(str(p))
    assert text == "ola mundo"


def test_returns_marker_on_api_error(fake_config, tmp_workdir):
    import config
    config.OPENAI_API_KEY = "sk-test"
    import transcribe

    p = tmp_workdir / "a.ogg"
    p.write_bytes(b"x")

    proc = MagicMock(stdout='{"error": {"message": "invalid"}}', stderr="", returncode=0)
    with patch("transcribe.subprocess.run", return_value=proc):
        text = transcribe.transcribe_audio(str(p))
    assert text.startswith("[audio - erro")


def test_returns_marker_when_file_missing(fake_config):
    import config
    config.OPENAI_API_KEY = "sk-test"
    import transcribe
    text = transcribe.transcribe_audio("/nonexistent.ogg")
    assert "nao encontrado" in text
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_transcribe.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `transcribe.py`**

```python
"""
Transcricao de audio via OpenAI Whisper.

Endpoint: POST https://api.openai.com/v1/audio/transcriptions
Modelo:   whisper-1
Aceita:   ogg, mp3, m4a, wav, mp4, webm (todos os formatos comuns).

Uso (CLI): python transcribe.py <audio_file>
"""
import json
import os
import subprocess
import sys

from config import OPENAI_API_KEY


WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


def transcribe_audio(path: str) -> str:
    """
    Returns transcript text on success.
    Returns bracketed marker on failure (never raises - keeps message flow alive).
    """
    if not OPENAI_API_KEY:
        return "[audio - transcricao desativada: configure OPENAI_API_KEY em config.py]"
    if not os.path.exists(path):
        return f"[audio - arquivo nao encontrado: {path}]"

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", WHISPER_URL,
                "-H", f"Authorization: Bearer {OPENAI_API_KEY}",
                "-F", "model=whisper-1",
                "-F", f"file=@{path}",
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
    except Exception as e:
        return f"[audio - erro de rede: {e}]"

    try:
        data = json.loads(result.stdout)
    except Exception:
        return "[audio - erro: resposta invalida do Whisper]"

    if "error" in data:
        msg = data["error"].get("message", "unknown") if isinstance(data["error"], dict) else str(data["error"])
        return f"[audio - erro: {msg}]"

    return (data.get("text") or "[audio - transcricao vazia]").strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    print(transcribe_audio(sys.argv[1]))
```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest tests/test_transcribe.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: transcribe.py - audio -> text via OpenAI Whisper"
```

---

## Task 7: webhook_server.py handles media

**Files:**
- Modify: `webhook_server.py`
- Create: `tests/test_webhook_parser.py`

Webhook will detect media, download it, and write `media_path`/`media_type` to JSONL. It will **NOT** auto-transcribe — Claude decides whether to call `transcribe.py`. Text for media-only messages becomes `[audio]` / `[image]` / caption.

- [ ] **Step 1: Write failing test**

```python
"""Tests for webhook payload parsing with media."""
import os
import sys
from unittest.mock import patch


def _import_ws():
    if "webhook_server" in sys.modules:
        del sys.modules["webhook_server"]
    import webhook_server
    return webhook_server


def test_text_unchanged(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "M1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "message": {"conversation": "ola"},
        "messageTimestamp": 1234,
    }
    msg = handler._parse(payload, session="1")
    assert msg["text"] == "ola"
    assert msg.get("media_path") is None
    assert msg.get("media_type") is None


def test_image_downloaded(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "IMG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "imageMessage",
        "message": {
            "imageMessage": {
                "url": "https://x/x.enc",
                "directPath": "/v/x.enc",
                "mediaKey": "K",
                "mimetype": "image/jpeg",
                "caption": "veja isso",
            }
        },
        "messageTimestamp": 1234,
    }

    def fake_download(session, msg_id, message_keys):
        os.makedirs(f"media/session{session}", exist_ok=True)
        p = f"media/session{session}/{msg_id}.jpg"
        with open(p, "wb") as f:
            f.write(b"X")
        return p

    with patch("webhook_server.media_handler.download_media", side_effect=fake_download):
        msg = handler._parse(payload, session="1")

    assert msg["media_type"] == "imageMessage"
    assert msg["media_path"].endswith("IMG1.jpg")
    assert msg["text"] == "veja isso"


def test_audio_no_autotranscribe(fake_config, tmp_workdir):
    """Webhook only downloads. Transcription is done by Claude on demand."""
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "AUD1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "audioMessage",
        "message": {
            "audioMessage": {
                "url": "https://x/a.enc",
                "directPath": "/v/a.enc",
                "mediaKey": "K",
                "mimetype": "audio/ogg; codecs=opus",
            }
        },
        "messageTimestamp": 1234,
    }

    def fake_download(session, msg_id, message_keys):
        os.makedirs(f"media/session{session}", exist_ok=True)
        p = f"media/session{session}/{msg_id}.ogg"
        with open(p, "wb") as f:
            f.write(b"X")
        return p

    with patch("webhook_server.media_handler.download_media", side_effect=fake_download):
        msg = handler._parse(payload, session="1")

    assert msg["media_type"] == "audioMessage"
    assert msg["media_path"].endswith("AUD1.ogg")
    assert msg["text"] == "[audio]"  # placeholder, NOT transcribed at webhook time


def test_image_without_caption_uses_placeholder(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)
    payload = {
        "key": {"id": "IMG2", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
        "pushName": "Geo",
        "messageType": "imageMessage",
        "message": {
            "imageMessage": {
                "url": "https://x/x.enc", "directPath": "/v/x.enc",
                "mediaKey": "K", "mimetype": "image/png",
            }
        },
        "messageTimestamp": 1234,
    }
    with patch("webhook_server.media_handler.download_media",
               return_value="media/session1/IMG2.png"):
        msg = handler._parse(payload, session="1")
    assert msg["text"] == "[image]"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_webhook_parser.py -v`
Expected: FAIL — webhook_server has no media handling.

- [ ] **Step 3: Modify `webhook_server.py`** — add import and rewrite `_parse`

After existing `from config import SESSIONS`, add:

```python
import media_handler
```

Replace the entire `_parse` method body with:

```python
    def _parse(self, data, session: str = "1"):
        try:
            key = data.get("key", {})
            jid = key.get("remoteJid", "") or data.get("jid", "")

            if "@g.us" in jid or "@newsletter" in jid:
                return None

            from_me = key.get("fromMe", False)
            phone = jid.replace("@s.whatsapp.net", "").replace("@lid", "")
            sess_phone = allowed_phone(session)

            is_self_chat = from_me and phone == sess_phone
            is_authorized_incoming = not from_me and phone == sess_phone

            if not is_self_chat and not is_authorized_incoming:
                return None

            msg_block = data.get("message", {}) or {}
            msg_id = key.get("id", "")

            message_type = media_handler.detect_message_type(data)
            media_path = None
            text = None

            if message_type:
                # Media path: download + extract caption (if any)
                keys = media_handler.extract_message_keys(msg_block, message_type)
                if keys:
                    media_path = media_handler.download_media(session, msg_id, keys)
                inner = msg_block.get(message_type, {}) or {}
                caption = inner.get("caption") if message_type != "audioMessage" else None
                kind_short = message_type.replace("Message", "")  # 'audio'/'image'/'video'
                text = caption or f"[{kind_short}]"
            else:
                text = (
                    msg_block.get("conversation")
                    or msg_block.get("extendedTextMessage", {}).get("text")
                    or "[unknown]"
                )

            return {
                "id":         msg_id,
                "from":       phone,
                "jid":        jid,
                "name":       data.get("pushName", ""),
                "text":       text,
                "ts":         data.get("messageTimestamp", 0),
                "fromMe":     from_me,
                "media_type": message_type,
                "media_path": media_path,
            }
        except Exception as e:
            print(f"PARSE_ERROR: {e}", flush=True)
            return None
```

- [ ] **Step 4: Run new tests, verify PASS**

Run: `python -m pytest tests/test_webhook_parser.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run full suite (regression check)**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add webhook_server.py tests/test_webhook_parser.py
git commit -m "feat(webhook): download image/audio/video, write media_path to JSONL"
```

---

## Task 8: send_image via megaAPI sendMediaMessage

**Files:**
- Modify: `send_message.py`
- Create: `tests/test_send_message.py`

**Pre-task verification (manual, ~2min):** Before coding, confirm the `sendMediaMessage` payload shape against megaAPI swagger. The implementation below assumes:

```
POST {MEGA_HOST}/rest/sendMessage/{instance}/mediaMessage
Body: {
  "messageData": {
    "to": "<phone>",
    "type": "image",
    "image": "<base64>",
    "caption": "<text>",
    "fileName": "<name>"
  }
}
```

This mirrors the `text` endpoint shape that already works. If megaAPI swagger shows a different envelope (e.g. `mediaMessage: {url, base64, ...}` or multipart upload), update Step 3 below before coding. Run a manual `curl` against the swagger example with one image first to confirm the shape returns `{error: false}`.

If unsure, paste the swagger snippet for `sendMediaMessage` here and I will adjust.

- [ ] **Step 1: Write failing test**

```python
"""Tests for send_message."""
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    if "send_message" in sys.modules:
        del sys.modules["send_message"]
    import send_message
    return send_message


def test_send_text_uses_text_endpoint(fake_config):
    sm = _import()
    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"ok": true}', stderr="", returncode=0)

    with patch("send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_text("5511888888888", "ola", "1")

    assert result == {"ok": True}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert url.endswith("/text")


def test_send_image_posts_media_endpoint_with_base64(fake_config, tmp_workdir):
    sm = _import()
    img = tmp_workdir / "x.jpg"
    img.write_bytes(b"IMGBYTES")

    captured = {}
    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(stdout='{"error": false}', stderr="", returncode=0)

    with patch("send_message.subprocess.run", side_effect=fake_run):
        result = sm.send_image("5511888888888", str(img), caption="legenda", session="1")

    assert result == {"error": False}
    url = captured["args"][captured["args"].index("POST") + 1]
    assert "/mediaMessage" in url

    # body should contain base64 of "IMGBYTES" (SU1HQllURVM=)
    body_idx = captured["args"].index("-d") + 1
    body = captured["args"][body_idx]
    assert "SU1HQllURVM=" in body
    assert "legenda" in body


def test_send_image_missing_file_returns_error(fake_config):
    sm = _import()
    result = sm.send_image("5511888888888", "/nonexistent.jpg", session="1")
    assert "error" in result
    assert "not found" in result["error"].lower()
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_send_message.py -v`
Expected: FAIL — `send_image` missing.

- [ ] **Step 3: Replace `send_message.py`**

```python
"""
Usage:
    python send_message.py <phone> <text> [session]
    python send_message.py --type image <phone> <path> [caption] [session]

Examples:
    python send_message.py 5511999999999 "Ola!" 1
    python send_message.py --type image 5511999999999 ./photo.jpg "veja" 1
"""
import base64
import json
import os
import subprocess
import sys

from config import SESSIONS, MEGA_HOST, SIGNATURE


TEXT_ENDPOINT  = "{host}/rest/sendMessage/{instance}/text"
MEDIA_ENDPOINT = "{host}/rest/sendMessage/{instance}/mediaMessage"


def _curl_json(url: str, payload_json: str, token: str) -> dict:
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", url,
                "-H", "accept: */*",
                "-H", f"Authorization: Bearer {token}",
                "-H", "Content-Type: application/json",
                "-d", payload_json,
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
    except Exception as e:
        return {"error": str(e)}
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stderr or result.stdout}


def send_text(phone: str, text: str, session: str = "1") -> dict:
    cfg = SESSIONS.get(session, SESSIONS["1"])
    url = TEXT_ENDPOINT.format(host=MEGA_HOST, instance=cfg["instance"])
    full_text = f"{text}\n\n{SIGNATURE}"
    payload = json.dumps({
        "messageData": {"to": phone, "text": full_text, "linkPreview": False}
    })
    return _curl_json(url, payload, cfg["token"])


def send_image(phone: str, image_path: str, caption: str = "", session: str = "1") -> dict:
    if not os.path.exists(image_path):
        return {"error": f"image not found: {image_path}"}

    cfg = SESSIONS.get(session, SESSIONS["1"])
    url = MEDIA_ENDPOINT.format(host=MEGA_HOST, instance=cfg["instance"])

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    full_caption = (f"{caption}\n\n{SIGNATURE}" if caption else SIGNATURE).strip()
    payload = json.dumps({
        "messageData": {
            "to":       phone,
            "type":     "image",
            "image":    b64,
            "caption":  full_caption,
            "fileName": os.path.basename(image_path),
        }
    })
    return _curl_json(url, payload, cfg["token"])


def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--type":
        if len(args) < 4 or args[1] != "image":
            print(__doc__)
            sys.exit(1)
        phone   = args[2]
        path    = args[3]
        caption = args[4] if len(args) > 4 else ""
        session = args[5] if len(args) > 5 else "1"
        print(json.dumps(send_image(phone, path, caption, session), indent=2, ensure_ascii=False))
    else:
        if len(args) < 2:
            print(__doc__)
            sys.exit(1)
        phone   = args[0]
        text    = args[1]
        session = args[2] if len(args) > 2 else "1"
        print(json.dumps(send_text(phone, text, session), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run new tests, verify PASS**

Run: `python -m pytest tests/test_send_message.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Live integration test (real megaAPI)**

```bash
# Use any small image in the project, or create one:
python -c "
from send_message import send_image
import json
result = send_image('556195562618', './tests/__init__.py', caption='teste', session='1')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

Wait — `__init__.py` is not an image. Use a real image. If you don't have one, skip Step 5 and confirm in Task 11 manual smoke test instead.

If the response is `{"error": "..."}` from megaAPI, the `mediaMessage` payload shape is wrong — open megaAPI swagger, find `sendMediaMessage`, fix Step 3 payload, rerun.

- [ ] **Step 6: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add send_message.py tests/test_send_message.py
git commit -m "feat(send): send_image via megaAPI mediaMessage endpoint"
```

---

## Task 9: doctor.py validates OPENAI_API_KEY

**Files:**
- Modify: `doctor.py`

- [ ] **Step 1: Add new check function** before `def main()`

```python
def check_openai():
    try:
        from config import OPENAI_API_KEY
    except ImportError:
        return
    if not OPENAI_API_KEY:
        warn("OPENAI_API_KEY vazio - transcricao de audio desativada")
        return
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
             "-H", f"Authorization: Bearer {OPENAI_API_KEY}",
             "https://api.openai.com/v1/models"],
            capture_output=True, text=True, timeout=10,
        )
        code = result.stdout.strip()
        if code == "200":
            ok("OpenAI API key valida (Whisper transcription disponivel)")
        elif code == "401":
            err("OpenAI API key invalida (401)")
        else:
            warn(f"OpenAI API: HTTP {code}")
    except Exception as e:
        warn(f"OpenAI API: erro ({e})")
```

- [ ] **Step 2: Call from `main()`** — after the `[MEGAAPI]` section, before `[FILES]`:

```python
    print("")
    print("[MULTIMODAL]")
    check_openai()
```

- [ ] **Step 3: Smoke test**

Run: `python doctor.py`
Expected: Output now has `[MULTIMODAL]` section.

- [ ] **Step 4: Commit**

```bash
git add doctor.py
git commit -m "feat(doctor): validate OPENAI_API_KEY"
```

---

## Task 10: CLAUDE_PROMPT.md + README + SETUP

**Files:**
- Modify: `CLAUDE_PROMPT.md`
- Modify: `README.md`
- Modify: `SETUP.md`

- [ ] **Step 1: Replace the main prompt block in `CLAUDE_PROMPT.md`**

Find the existing prompt code-block (starts with `Voce e um agente WhatsApp.`) and replace its contents with:

```
Voce e um agente WhatsApp multimodal. Sua tarefa:

1. Use a ferramenta Monitor para rodar:
   python monitor.py 1

2. Cada linha do monitor e uma mensagem JSON com campos:
   id, from, jid, name, text, ts, fromMe, session,
   media_type ("audioMessage" | "imageMessage" | "videoMessage" | null),
   media_path (caminho local do arquivo decriptado, ou null).

3. Para cada mensagem nova:

   a. Se text comeca com "!CMD_TOKEN " (use o valor real de config.py),
      remova o prefixo e processe o restante como tarefa.
      Senao, IGNORE silenciosamente.

   b. Se media_type == "audioMessage" e media_path existir:
      - Rode: python transcribe.py <media_path>
      - Use a transcricao como pergunta/comando do usuario.
      - Se OPENAI_API_KEY nao estiver configurada, transcribe.py retorna
        "[audio - transcricao desativada...]" - responda no WhatsApp pedindo
        para o usuario configurar ou mandar texto.

   c. Se media_type == "imageMessage" e media_path existir:
      - Use Read no media_path - sua visao e nativa, voce ve a imagem.
      - text contem a legenda (caption) ou "[image]" se sem legenda.
      - Analise e responda em texto.

   d. Se media_type == "videoMessage":
      - Responda: "Videos nao sao suportados ainda."

   e. Texto puro: trate normalmente.

4. Resposta:
   - Texto:   python send_message.py <from> "<resposta>" 1
   - Imagem:  python send_message.py --type image <from> <caminho> "<legenda>" 1

5. NUNCA processe mensagens cujo text contenha "*Claude Code*" (loop guard
   - sao suas proprias respostas voltando via webhook).

6. Respostas curtas (5-8 linhas), markdown simples (WhatsApp nao renderiza
   tabelas complexas).

7. Em erro:
   python send_message.py <from> "Erro: <descricao>. Tente reformular." 1

Comece agora.
```

- [ ] **Step 2: Append to `CLAUDE_PROMPT.md`** — new section after the existing variations:

```markdown
## Adicionar nova sessao

Para conectar mais um numero WhatsApp ao mesmo deployment:

1. `python add_session.py` (wizard pergunta instance/token/phone)
2. No painel megaAPI da nova instancia, configure webhook como `<URL_NGROK>/?session=N`
3. Mande 1 msg pra voce mesmo no novo numero
4. `python discover_lid.py N`
5. Em outra sessao Claude Code: cole o mesmo prompt acima trocando
   `monitor.py 1` por `monitor.py N` e `... 1` por `... N` no send.

Cada sessao Claude Code = 1 numero = 1 instancia. Sessoes independentes.
```

- [ ] **Step 3: Update `README.md`** — replace the "Multi-sessão" section with:

```markdown
## Multi-sessão

Adicionar nova instancia ao deployment ja rodando:

```bash
python add_session.py
```

O wizard atribui o proximo ID livre. Configure o webhook da nova instancia
megaAPI como `https://abc.ngrok.app/?session=N`. Cada sessao roda em
sua propria sessao Claude Code (`python monitor.py N`).

## Multimodal

| Direcao | Texto | Imagem | Audio |
|---------|-------|--------|-------|
| Recebe  | OK    | OK (Claude le via Read tool) | OK (Whisper transcreve) |
| Envia   | OK    | OK (`--type image`) | nao suportado |

Multimodal e opcional: sem `OPENAI_API_KEY`, recebimento de audio ainda
funciona (arquivo salvo em `media/sessionN/`), mas sem transcricao automatica.
```

- [ ] **Step 4: Update `SETUP.md`** — append after section "9. Multi-sessão":

```markdown
## 10. Multimodal (opcional)

### 10.1 Receber audio com transcricao

1. Crie conta em https://platform.openai.com
2. Gere API key em https://platform.openai.com/api-keys
3. Edite `config.py`: `OPENAI_API_KEY = "sk-..."`
4. Reinicie webhook: `./stop.sh && ./start.sh`
5. Mande audio no WhatsApp. Claude roda `python transcribe.py <path>` e
   responde com base no texto transcrito.

### 10.2 Receber imagens
Funciona automaticamente. Imagem decriptada vai pra `media/sessionN/<id>.jpg`.
Claude usa `Read` no arquivo (visao nativa) e descreve.

### 10.3 Enviar imagens
```bash
python send_message.py --type image 5511999999999 ./foto.jpg "minha legenda" 1
```

## 11. Adicionar nova instancia
```bash
python add_session.py
```
Configure webhook da nova: `<URL_NGROK>/?session=N`. Em outra sessao
Claude Code: `python monitor.py N`.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE_PROMPT.md README.md SETUP.md
git commit -m "docs: multimodal + multi-session usage"
```

---

## Task 11: Final integration sweep

**Files:** none (validation only)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (~17 tests across all modules).

- [ ] **Step 2: Compile-check every Python file**

Run:
```bash
python -m py_compile webhook_server.py monitor.py send_message.py \
    config.py config.example.py setup_config.py discover_lid.py \
    doctor.py add_session.py media_handler.py transcribe.py
```
Expected: no output.

- [ ] **Step 3: Doctor against live deployment**

Run: `python doctor.py`
Expected: ENV/CONFIG/RUNTIME/MEGAAPI/MULTIMODAL/FILES all OK or expected WARN.

- [ ] **Step 4: Manual end-to-end smoke test**

Verify each path manually with the agent running in Claude Code:

| # | Action | Expected |
|---|--------|----------|
| 1 | Send TEXT `!<TOK> ping` | Claude replies in text within ~5s |
| 2 | Send IMAGE with caption `!<TOK> o que tem na foto?` | Claude opens image, describes in text |
| 3 | Send AUDIO saying `!<TOK> conte uma piada` | Claude transcribes via Whisper, responds in text |
| 4 | Send VIDEO | Claude replies "Videos nao suportados" |
| 5 | Run `python add_session.py` (with 2nd instance ready) | New `"2"` block appears in `config.py` |
| 6 | Send IMAGE from agent: `python send_message.py --type image <phone> <path> "legenda" 1` | Image arrives in WhatsApp with caption + signature |

Document any failures inline:
```
Path 1 (text in/out):       [PASS / FAIL - reason]
Path 2 (image in / text out):[PASS / FAIL - reason]
Path 3 (audio in / text out):[PASS / FAIL - reason]
Path 4 (video rejected):    [PASS / FAIL - reason]
Path 5 (add session):       [PASS / FAIL - reason]
Path 6 (image out):         [PASS / FAIL - reason]
```

- [ ] **Step 5: Final commit if anything changed during sweep**

```bash
git status
# if anything changed:
git add <files>
git commit -m "chore: final fixes for trilha 1"
```

- [ ] **Step 6: Tag release**

```bash
git tag -a v1.0-trilha1 -m "Trilha 1: multi-session + multimodal POC"
```

---

## Done Criteria

- [ ] ~17 unit tests pass
- [ ] doctor.py shows OK for all configured features
- [ ] All 6 manual smoke paths verified
- [ ] README + SETUP + CLAUDE_PROMPT accurate and current
- [ ] Git tagged `v1.0-trilha1`
- [ ] Ready to start Trilha 2 (VPS + Cloudflare Tunnel)
