# OSS Distribution & One-Command Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform `whatsapp-claude-agent` from a personal POC into an open-source-ready project with one-command bootstrap, Cloudflare Tunnel as default tunnel, polished docs, license, CI, and a repo layout that scales (src/scripts/docs/tests).

**Architecture:** A single new entrypoint `bootstrap.py` orchestrates everything (deps check, config wizard, webhook server, Quick Tunnel via cloudflared, automatic megaAPI webhook push). `start/stop` scripts are simplified to manage only webhook + tunnel processes. Documentation is split into role-targeted files (README quickstart, SETUP walkthrough, TROUBLESHOOTING, CONTRIBUTING). Source code is moved into a `src/whatsapp_agent/` package, scripts to `scripts/`, tests already in `tests/`. CI runs pytest on every push. Repo gets MIT license, CHANGELOG, GitHub templates, and a `pyproject.toml` so users can install via `pip install -e .`.

**Tech Stack:** Python 3.8+, cloudflared (winget/brew/apt), pytest, GitHub Actions, megaAPI (existing), Claude Code CLI (existing). No new runtime deps — only dev/distribution scaffolding.

**Scope note:** This plan is large but coherent — every task contributes to "ship a v1.0 OSS release". Tasks are ordered so each is self-contained and testable. The repo reorg (Tasks 13-15) is the riskiest phase and is gated by all prior tasks landing first. No reorg until docs+CI are green.

---

## File Structure

### New files (created by this plan)

| Path | Responsibility |
|------|----------------|
| `bootstrap.py` | Single entrypoint: deps → config → webhook → tunnel → megaAPI push → ready. |
| `LICENSE` | MIT license text. |
| `CHANGELOG.md` | Human-readable history starting at v1.0. |
| `CONTRIBUTING.md` | How to contribute, dev setup, test commands, commit style. |
| `TROUBLESHOOTING.md` | Symptom → fix table for common boot/runtime issues. |
| `pyproject.toml` | PEP 621 metadata, optional `pip install -e .`, console_scripts. |
| `.github/workflows/ci.yml` | Pytest matrix on push/PR. |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Bug template. |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Feature template. |
| `.github/pull_request_template.md` | PR checklist. |
| `tests/test_bootstrap.py` | Tests for new bootstrap helpers. |
| `tests/test_update_webhooks.py` | Tests for webhook push helper. |

### Files moved (in reorg phase)

| From | To |
|------|----|
| `webhook_server.py` | `src/whatsapp_agent/webhook_server.py` |
| `monitor.py` | `src/whatsapp_agent/monitor.py` |
| `send_message.py` | `src/whatsapp_agent/send_message.py` |
| `media_handler.py` | `src/whatsapp_agent/media_handler.py` |
| `transcribe.py` | `src/whatsapp_agent/transcribe.py` |
| `update_webhooks.py` | `src/whatsapp_agent/update_webhooks.py` |
| `doctor.py` | `src/whatsapp_agent/doctor.py` |
| `add_session.py` | `src/whatsapp_agent/add_session.py` |
| `discover_lid.py` | `src/whatsapp_agent/discover_lid.py` |
| `setup_config.py` | `src/whatsapp_agent/setup_config.py` |
| `config.py` / `config.example.py` | stays at repo root (user-edited, not packaged) |
| `start.{ps1,sh}` `stop.{ps1,sh}` `install.{ps1,sh}` | `scripts/` |
| `bootstrap.py` | `scripts/bootstrap.py` (after Task 4 lands at root, moved in Task 14) |

### Files modified (no move)

`README.md`, `SETUP.md`, `CLAUDE_PROMPT.md`, `PROJETO.md`, `.gitignore`, `start.{sh,ps1}`, `stop.{sh,ps1}`, `install.{sh,ps1}`, `doctor.py`, `setup_config.py`, all `tests/test_*.py` (import paths in reorg phase).

---

## Task 1: Baseline — capture green test state

**Why:** Before any change, prove the current main works. Any regression after this point is owned by this plan.

**Files:**
- Read-only

- [ ] **Step 1: Run full test suite from a clean shell**

Run: `py -m pytest -q`
Expected: all tests pass (currently 26 tests). Record exit code 0.

- [ ] **Step 2: Run doctor against live system**

Run: `py doctor.py`
Expected: all `[OK]` lines (Python, curl, config, webhook port, tunnel publico, megaAPI sessões, OpenAI key, files). At most one `[WARN]` for `cloudflared` PATH (acceptable — winget didn't reload PATH).

- [ ] **Step 3: Snapshot git state**

Run:
```bash
git status > /tmp/baseline-status.txt
git rev-parse HEAD > /tmp/baseline-sha.txt
```

Expected: branch `trilha-1-multimodal`, working tree has the in-progress changes from the cloudflared session (config.py, doctor.py, start/stop, .gitignore, update_webhooks.py, CLAUDE_PROMPT.md). These are in-flight changes that belong to a separate feat commit before this plan starts — see Task 2 step 1.

- [ ] **Step 4: Commit pre-existing cloudflared work**

Run:
```bash
git add config.py update_webhooks.py doctor.py start.sh start.ps1 stop.sh stop.ps1 .gitignore CLAUDE_PROMPT.md
git diff --cached --stat
git commit -m "feat(tunnel): switch ngrok to Cloudflare Tunnel + parametric Monitor session

- config.PUBLIC_WEBHOOK_URL becomes single source of truth
- update_webhooks.py pushes URL to all megaAPI SESSIONS via configWebhook
- start/stop scripts manage only webhook (tunnel runs as service)
- doctor checks cloudflared + tunnel reachability via POST
- CLAUDE_PROMPT placeholder <SESSAO> + 'SESSAO: N' marker for multi-session
- .gitignore covers .pid.* and ngrok_url.txt"
```

Expected: clean working tree afterward except untracked `.pid.*`, `ngrok_url.txt`, `docs/plans/2026-04-28-trilha-2-vps-deploy.md`. These stay untracked.

---

## Task 2: LICENSE (MIT)

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Write LICENSE**

Create `LICENSE` with:

```
MIT License

Copyright (c) 2026 Geovani Junior <sitecasadainfo2011@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "chore: add MIT license"
```

---

## Task 3: CHANGELOG.md (Keep a Changelog format)

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write CHANGELOG**

Create `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- One-command bootstrap (`python bootstrap.py`) with Quick Tunnel.
- Cloudflare Tunnel support replacing ngrok.
- `update_webhooks.py` to push webhook URL to all megaAPI sessions.
- Parametric `<SESSAO>` placeholder in `CLAUDE_PROMPT.md` for multi-session reuse.
- MIT license, CONTRIBUTING, TROUBLESHOOTING, GitHub issue/PR templates.
- CI workflow running pytest on every push.
- `pyproject.toml` for `pip install -e .` developer install.

### Changed
- Repository reorganized: source under `src/whatsapp_agent/`, scripts under `scripts/`.
- README rewritten for OSS audience.

### Removed
- ngrok references in scripts and docs (kept as historical mention only).

## [1.0.0-trilha1] — 2026-04-28

### Added
- Multi-session support (multiple WhatsApp instances per deployment).
- Multimodal: image (Claude Read tool), audio (OpenAI Whisper), text in/out.
- `add_session.py` wizard, `discover_lid.py`, `media_handler.py`, `transcribe.py`.
- 26 pytest tests.

[Unreleased]: https://github.com/mbkautomacoes/zyon/compare/v1.0-trilha1...HEAD
[1.0.0-trilha1]: https://github.com/mbkautomacoes/zyon/releases/tag/v1.0-trilha1
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG (Keep a Changelog format)"
```

---

## Task 4: bootstrap.py — failing test first (TDD)

**Why:** `bootstrap.py` is the new front door. Test the URL-extraction logic in isolation before wiring orchestration.

**Files:**
- Create: `tests/test_bootstrap.py`
- Create: `bootstrap.py`

- [ ] **Step 1: Write the failing test for `extract_quick_tunnel_url`**

Create `tests/test_bootstrap.py`:

```python
"""Tests for bootstrap.py orchestration helpers."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from bootstrap import extract_quick_tunnel_url


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_bootstrap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bootstrap'`.

- [ ] **Step 3: Implement minimal `extract_quick_tunnel_url`**

Create `bootstrap.py`:

```python
"""
WhatsApp Claude Agent — one-command bootstrap.

Runs deps check, config wizard, webhook server, Quick Tunnel via cloudflared,
captures the public URL, persists it in config.PUBLIC_WEBHOOK_URL, and pushes
it to every megaAPI session registered in config.SESSIONS.

Usage: python bootstrap.py
"""
import re
from typing import Optional


_QUICK_TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def extract_quick_tunnel_url(log_text: str) -> Optional[str]:
    """Find the trycloudflare.com URL inside cloudflared stdout/stderr."""
    match = _QUICK_TUNNEL_RE.search(log_text)
    return match.group(0) if match else None


if __name__ == "__main__":
    raise SystemExit("bootstrap.main is implemented in Task 5; only helpers exist now.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_bootstrap.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add bootstrap.py tests/test_bootstrap.py
git commit -m "feat(bootstrap): add Quick Tunnel URL extractor (TDD)"
```

---

## Task 5: bootstrap.py — orchestrator (deps + config + tunnel + push)

**Files:**
- Modify: `bootstrap.py`

- [ ] **Step 1: Add dependency-check + cloudflared-locator logic to `bootstrap.py`**

Replace the `if __name__ == "__main__":` block at the bottom of `bootstrap.py` with the full orchestrator. Append after the existing `extract_quick_tunnel_url`:

```python
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def find_cloudflared() -> Optional[str]:
    """Return path to cloudflared.exe / cloudflared, or None."""
    direct = shutil.which("cloudflared")
    if direct:
        return direct
    if sys.platform == "win32":
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / (
            "Microsoft/WinGet/Packages/"
            "Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe/"
            "cloudflared.exe"
        )
        if winget.exists():
            return str(winget)
    return None


def check_python() -> None:
    if sys.version_info < (3, 8):
        sys.exit(f"ERROR: Python 3.8+ required (you have {sys.version.split()[0]}).")


def check_curl() -> None:
    if not shutil.which("curl"):
        sys.exit("ERROR: curl not found. Install it and re-run.")


def ensure_config() -> None:
    if Path("config.py").exists():
        return
    print("[bootstrap] config.py not found — running wizard...")
    code = subprocess.call([sys.executable, "setup_config.py"])
    if code != 0 or not Path("config.py").exists():
        sys.exit("ERROR: config wizard did not produce config.py.")


def start_webhook() -> subprocess.Popen:
    print("[bootstrap] starting webhook_server.py on :3020...")
    log = open("webhook.log", "ab")
    proc = subprocess.Popen(
        [sys.executable, "webhook_server.py"],
        stdout=log, stderr=log,
    )
    time.sleep(2)
    if proc.poll() is not None:
        sys.exit("ERROR: webhook_server.py exited immediately. Check webhook.log.")
    return proc


def start_quick_tunnel(cloudflared_path: str) -> tuple[subprocess.Popen, str]:
    print("[bootstrap] starting Quick Tunnel via cloudflared...")
    log_path = Path("cloudflared.log")
    log = open(log_path, "wb")
    proc = subprocess.Popen(
        [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:3020"],
        stdout=log, stderr=log,
    )
    deadline = time.time() + 30
    url: Optional[str] = None
    while time.time() < deadline:
        time.sleep(1)
        if proc.poll() is not None:
            sys.exit("ERROR: cloudflared exited. Check cloudflared.log.")
        url = extract_quick_tunnel_url(log_path.read_text(encoding="utf-8", errors="ignore"))
        if url:
            break
    if not url:
        proc.terminate()
        sys.exit("ERROR: cloudflared did not print a Quick Tunnel URL within 30s.")
    print(f"[bootstrap] tunnel up: {url}")
    return proc, url


def write_public_url(url: str) -> None:
    """Update config.PUBLIC_WEBHOOK_URL in-place (or append if missing)."""
    text = Path("config.py").read_text(encoding="utf-8")
    if "PUBLIC_WEBHOOK_URL" in text:
        new = re.sub(
            r'PUBLIC_WEBHOOK_URL\s*=\s*".*?"',
            f'PUBLIC_WEBHOOK_URL = "{url}"',
            text,
        )
    else:
        new = text + f'\n\nPUBLIC_WEBHOOK_URL = "{url}"\n'
    Path("config.py").write_text(new, encoding="utf-8")


def push_webhooks() -> None:
    print("[bootstrap] pushing webhook URL to megaAPI sessions...")
    code = subprocess.call([sys.executable, "update_webhooks.py"])
    if code != 0:
        sys.exit("ERROR: update_webhooks.py failed.")


def main() -> int:
    print("=" * 60)
    print("WhatsApp Claude Agent - Bootstrap")
    print("=" * 60)
    check_python()
    check_curl()
    cf = find_cloudflared()
    if not cf:
        sys.exit(
            "ERROR: cloudflared not found.\n"
            "  Windows: winget install Cloudflare.cloudflared\n"
            "  macOS:   brew install cloudflared\n"
            "  Linux:   see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        )
    ensure_config()
    webhook = start_webhook()
    tunnel, url = start_quick_tunnel(cf)
    write_public_url(url)
    push_webhooks()
    print("")
    print("=" * 60)
    print("READY")
    print("=" * 60)
    print(f"  Public URL: {url}")
    print(f"  Webhook PID: {webhook.pid}  (logs: webhook.log)")
    print(f"  Tunnel  PID: {tunnel.pid}   (logs: cloudflared.log)")
    print("")
    print("Next:")
    print("  1. Open another terminal: claude")
    print("  2. Paste: 'Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1'")
    print("  3. Send a WhatsApp message to your number.")
    print("")
    print("To stop everything: ./stop.sh   (or .\\stop.ps1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Add a smoke test that imports `main` without running it**

Append to `tests/test_bootstrap.py`:

```python
def test_main_is_callable():
    import bootstrap
    assert callable(bootstrap.main)
    assert callable(bootstrap.find_cloudflared)
```

- [ ] **Step 3: Run tests**

Run: `py -m pytest tests/test_bootstrap.py -v`
Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add bootstrap.py tests/test_bootstrap.py
git commit -m "feat(bootstrap): one-command orchestrator (deps + config + tunnel + megaAPI push)"
```

---

## Task 6: update_webhooks.py — guard tests

**Why:** `update_webhooks.py` is now a documented entrypoint. Lock its behavior with a test.

**Files:**
- Create: `tests/test_update_webhooks.py`

- [ ] **Step 1: Write tests using monkeypatch**

Create `tests/test_update_webhooks.py`:

```python
"""Tests for update_webhooks.configure (no real network)."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def fake_config(monkeypatch, tmp_path):
    fake = types.ModuleType("config")
    fake.PUBLIC_WEBHOOK_URL = "https://example.test"
    fake.MEGA_HOST = "https://mega.example"
    fake.SESSIONS = {
        "1": {"instance": "inst-1", "token": "tok-1"},
        "2": {"instance": "inst-2", "token": "tok-2"},
    }
    monkeypatch.setitem(sys.modules, "config", fake)
    return fake


def test_configure_success(fake_config, monkeypatch):
    import update_webhooks

    captured = {}

    class FakeResult:
        stdout = '{"error": false, "message": "Webhooks configured"}'

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(update_webhooks.subprocess, "run", fake_run)

    ok = update_webhooks.configure("1", "inst-1", "tok-1")
    assert ok is True
    body = json.loads(captured["cmd"][captured["cmd"].index("-d") + 1])
    assert body["messageData"]["webhookUrl"] == "https://example.test/?session=1"
    assert body["messageData"]["webhookEnabled"] is True


def test_configure_failure_returns_false(fake_config, monkeypatch):
    import update_webhooks

    class FakeResult:
        stdout = '{"error": true, "message": "bad token"}'

    monkeypatch.setattr(
        update_webhooks.subprocess,
        "run",
        lambda *a, **kw: FakeResult(),
    )
    assert update_webhooks.configure("1", "inst-1", "tok-1") is False
```

- [ ] **Step 2: Run tests**

Run: `py -m pytest tests/test_update_webhooks.py -v`
Expected: 2 tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_update_webhooks.py
git commit -m "test: cover update_webhooks.configure success+failure paths"
```

---

## Task 7: README rewrite (cloudflared default, OSS audience)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite README**

Overwrite `README.md` with:

```markdown
# WhatsApp Claude Agent

Self-hosted WhatsApp agent that uses **Claude Code CLI** as the LLM engine
(no extra API key for the LLM itself). Receives WhatsApp messages via the
[megaAPI](https://megaapi.com.br) webhook and replies through Claude Code.

[![CI](https://github.com/mbkautomacoes/zyon/actions/workflows/ci.yml/badge.svg)](https://github.com/mbkautomacoes/zyon/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## TL;DR

```bash
git clone https://github.com/mbkautomacoes/zyon.git whatsapp-claude-agent
cd whatsapp-claude-agent
python bootstrap.py
```

`bootstrap.py` runs the config wizard, starts the webhook server, opens a
Cloudflare Quick Tunnel, and pushes the public URL to your megaAPI session.
Then you open Claude Code and paste a one-liner. Done.

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.8+ | runtime | https://python.org |
| curl | HTTP calls | bundled on Windows 10+, Linux, macOS |
| cloudflared | public tunnel | `winget install Cloudflare.cloudflared` / `brew install cloudflared` / [docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| Claude Code CLI | the brain | https://docs.anthropic.com/claude-code |
| megaAPI account | WhatsApp gateway | https://megaapi.com.br (paid SaaS) |
| OpenAI API key (optional) | audio transcription | https://platform.openai.com/api-keys |

## Architecture

```
WhatsApp → megaAPI → Cloudflare Tunnel → webhook_server.py → messages_sessionN.jsonl
                                                                     ↓
WhatsApp ← megaAPI ← send_message.py ← Claude Code session ← monitor.py (Monitor tool)
```

1. `webhook_server.py` listens on `:3020`, validates the whitelisted phone, writes JSONL.
2. `monitor.py N` tails the per-session JSONL — runs **inside** a Claude Code session via the Monitor tool.
3. Claude Code reads each JSON line as user input, processes it, and replies via `send_message.py`.
4. Cloudflare Tunnel (Quick by default, named tunnel for production) exposes `:3020` over HTTPS.

## Two tunnel modes

**Quick Tunnel (default, zero-config):** random `*.trycloudflare.com` URL, regenerated each run, no domain needed. Used by `bootstrap.py`.

**Named Tunnel (production):** stable subdomain on a domain you control in Cloudflare. See [SETUP.md § Named Tunnel](SETUP.md#named-tunnel).

## Multi-session

One deployment can serve multiple WhatsApp instances:

```bash
python add_session.py    # wizard to add session 2, 3, ...
python update_webhooks.py # re-pushes URL to all sessions
```

Open one Claude Code session per WhatsApp session and paste:
`Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: <N>`

## Multimodal

| Direction | Text | Image | Audio | Video |
|-----------|------|-------|-------|-------|
| Receive | yes | yes (Claude reads natively) | yes (Whisper, optional) | rejected |
| Send | yes | yes (`send_message.py --type image`) | no | no |

## Repo layout

```
.
├── bootstrap.py          # one-command install/run
├── webhook_server.py     # HTTP :3020 receiver
├── monitor.py            # JSONL tail (Monitor target)
├── send_message.py       # outbound megaAPI client
├── update_webhooks.py    # push PUBLIC_WEBHOOK_URL to all sessions
├── doctor.py             # diagnostics
├── add_session.py        # wizard to add another WhatsApp session
├── discover_lid.py       # auto-fill LID after first message
├── media_handler.py      # decrypt+save media via megaAPI
├── transcribe.py         # OpenAI Whisper wrapper
├── setup_config.py       # interactive config wizard
├── config.example.py     # template (copy to config.py — gitignored)
├── start.{sh,ps1}        # start webhook only (tunnel manages itself)
├── stop.{sh,ps1}         # stop webhook
├── tests/                # pytest
├── docs/                 # extended docs and roadmaps
├── CLAUDE_PROMPT.md      # paste into Claude Code to activate the agent
├── SETUP.md              # step-by-step walkthrough (megaAPI signup, tunnel modes)
├── TROUBLESHOOTING.md    # symptom → fix
├── CONTRIBUTING.md
├── CHANGELOG.md
└── LICENSE               # MIT
```

## Documentation

- **[SETUP.md](SETUP.md)** — full walkthrough including megaAPI account creation and named tunnel.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — common boot/runtime issues.
- **[CLAUDE_PROMPT.md](CLAUDE_PROMPT.md)** — the prompt that activates the agent inside Claude Code.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — dev setup, test commands, commit style.
- **[PROJETO.md](PROJETO.md)** — architecture deep-dive, megaAPI quirks, decision log.
- **[CHANGELOG.md](CHANGELOG.md)** — release history.

## Security

- `config.py` is **gitignored** — your tokens never leave your machine.
- Whitelist by phone number — only your authorized number(s) trigger the agent.
- Loop guard via `*Claude Code*` signature — the agent never replies to its own messages.
- Self-chat is supported (sending to yourself).

## License

MIT — see [LICENSE](LICENSE).

## Status

- Branch `trilha-1-multimodal` (tag `v1.0-trilha1`) — multi-session + multimodal validated end-to-end on 2026-04-28.
- Tunnel migrated from ngrok to Cloudflare Tunnel.
- Trilha 2 (24/7 VPS deploy) — see `docs/plans/2026-04-28-trilha-2-vps-deploy.md`.
```

- [ ] **Step 2: Verify no broken internal links**

Run:
```bash
grep -nE '\]\(\./?[A-Z]' README.md
```
Expected output: each linked file (`SETUP.md`, `TROUBLESHOOTING.md`, `CLAUDE_PROMPT.md`, `CONTRIBUTING.md`, `PROJETO.md`, `CHANGELOG.md`, `LICENSE`) — `TROUBLESHOOTING.md` and `CONTRIBUTING.md` won't exist yet; that's fine — they land in Tasks 9 and 10.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): rewrite for OSS audience, cloudflared default"
```

---

## Task 8: SETUP.md rewrite (megaAPI walkthrough + named tunnel)

**Files:**
- Modify: `SETUP.md`

- [ ] **Step 1: Read current SETUP.md**

Run: `cat SETUP.md`
Expected: existing 193-line file. Note any sections worth keeping (e.g. multi-session example).

- [ ] **Step 2: Overwrite SETUP.md**

Replace with:

```markdown
# Setup walkthrough

This is the slow path. If you just want to try the agent, follow the
[README TL;DR](README.md#tldr) instead.

## 1. Create a megaAPI account and instance

1. Sign up at https://megaapi.com.br.
2. In the dashboard, create a new instance. Note the **instance name**
   (e.g. `megabusiness-yourname`) and the **token**.
3. Connect a WhatsApp number to the instance — scan the QR code with
   the WhatsApp app on the phone.
   _If you have a screenshot of this step, drop it into `docs/images/megaapi-qr.png`
   and reference it here._

## 2. Install dependencies

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| Python 3.8+ | https://python.org or `winget install Python.Python.3.12` | `brew install python` | `apt install python3` |
| cloudflared | `winget install Cloudflare.cloudflared` | `brew install cloudflared` | https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ |
| Claude Code CLI | https://docs.anthropic.com/claude-code | same | same |

## 3. Clone and bootstrap

```bash
git clone https://github.com/mbkautomacoes/zyon.git whatsapp-claude-agent
cd whatsapp-claude-agent
python bootstrap.py
```

`bootstrap.py` will:

1. Verify Python, curl, and cloudflared are present.
2. Run the config wizard if `config.py` does not exist (asks for instance, token, phone, optional OpenAI key).
3. Start `webhook_server.py` on `:3020`.
4. Open a Cloudflare Quick Tunnel and capture the public URL.
5. Write `PUBLIC_WEBHOOK_URL` into `config.py`.
6. Run `update_webhooks.py` to push the URL to every megaAPI session.
7. Print a "READY" banner with the URL and the next step.

## 4. Discover your LID

Send any WhatsApp message to your own number. Then run:

```bash
python discover_lid.py
```

This reads `messages_session1.jsonl`, extracts the LID, and writes it back into `config.py`. Without the LID, the whitelist cannot match LID-based group messages.

## 5. Activate Claude Code

Open a new terminal:

```bash
cd whatsapp-claude-agent
claude
```

In the Claude Code session, send as the first message:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1
```

Claude will read the prompt, run `python doctor.py`, activate the Monitor tool on `python monitor.py 1`, and start replying to incoming WhatsApp messages.

## 6. Test it

Send any text message to your WhatsApp number. Claude replies within seconds, signed `*Claude Code*`.

## Multi-session

Add another WhatsApp instance:

```bash
python add_session.py        # asks for instance/token/phone, assigns next ID
python update_webhooks.py    # re-pushes PUBLIC_WEBHOOK_URL to all sessions
```

Open a second Claude Code session in another terminal and paste:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 2
```

Each Claude Code session monitors **exactly one** WhatsApp session.

## Named Tunnel (production)

Quick Tunnel URLs are random and regenerate on every restart. For a stable URL, switch to a named tunnel.

```bash
cloudflared tunnel login
cloudflared tunnel create whatsapp-webhook
cloudflared tunnel route dns whatsapp-webhook agent.your-domain.com
```

Edit `~/.cloudflared/config.yml`:

```yaml
tunnel: <tunnel-id-printed-by-create>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: agent.your-domain.com
    service: http://127.0.0.1:3020
  - service: http_status:404
```

Update `config.PUBLIC_WEBHOOK_URL` to `https://agent.your-domain.com` and run `python update_webhooks.py`.

Run the tunnel as a background service:

```bash
# Linux: systemd unit (sudo cloudflared service install)
# Windows (admin PowerShell):
cloudflared service install
```

## Stopping

```bash
./stop.sh        # Linux/macOS
.\stop.ps1       # Windows
```

This stops the webhook. The Cloudflare Tunnel is managed separately (Quick Tunnel exits when the spawning shell does; named tunnel runs as a service).

## Diagnostics

```bash
python doctor.py
```

Prints `[OK]` / `[WARN]` / `[ERRO]` for each component. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes.
```

- [ ] **Step 3: Commit**

```bash
git add SETUP.md
git commit -m "docs(setup): rewrite walkthrough for cloudflared + bootstrap"
```

---

## Task 9: TROUBLESHOOTING.md

**Files:**
- Create: `TROUBLESHOOTING.md`

- [ ] **Step 1: Write TROUBLESHOOTING**

Create `TROUBLESHOOTING.md`:

```markdown
# Troubleshooting

When in doubt, run `python doctor.py` first. It prints the state of every component.

## Boot

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bootstrap.py` exits "ERROR: cloudflared not found" | binary not on PATH | `winget install Cloudflare.cloudflared` (Windows), `brew install cloudflared` (macOS), or download from Cloudflare. |
| `bootstrap.py` exits "ERROR: cloudflared did not print a Quick Tunnel URL" | Cloudflare blocked the run, or the network has outbound QUIC blocked | check `cloudflared.log` for the real error. Re-run with `cloudflared tunnel --url http://127.0.0.1:3020 --protocol http2` if QUIC is blocked. |
| `webhook_server.py` exits immediately | `:3020` is in use | `lsof -iTCP:3020 -sTCP:LISTEN` (Linux/macOS) or `netstat -ano \| findstr :3020` (Windows) — kill the offending process. |
| `setup_config.py` runs every time | `config.py` was deleted or never written | run `python setup_config.py` once and verify the file lands in the project root. |

## megaAPI

| Symptom | Cause | Fix |
|---------|-------|-----|
| `doctor.py` reports `megaAPI sessao N: HTTP 404` | wrong instance name | check the instance string in `config.py` matches the megaAPI dashboard. |
| `doctor.py` reports `megaAPI sessao N: HTTP 401` | bad token | regenerate the token in the megaAPI dashboard, update `config.py`, run `python update_webhooks.py`. |
| Webhook never fires | URL not registered or instance disconnected | run `python update_webhooks.py`; verify the WhatsApp connection in the megaAPI dashboard. |

## Runtime

| Symptom | Cause | Fix |
|---------|-------|-----|
| Message arrives in JSONL but Claude does not reply | no Claude Code session has the Monitor tool active on `python monitor.py N` | open a Claude Code session and paste `Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: N`. |
| Two replies for one message | duplicate `monitor.py` processes | `ps -ef \| grep monitor.py \| grep -v grep` — kill all but one. |
| `monitor.py` runs but messages are silently dropped | `monitor.py` was launched standalone (nohup/&) — its stdout has no consumer; it marks every message as processed | kill it (`pkill -f "monitor.py"`), then activate it inside a Claude Code session via the Monitor tool. |
| Replies loop infinitely | the loop guard signature `*Claude Code*` was removed from outgoing messages | restore `SIGNATURE = "*Claude Code*"` in `config.py`. |
| Image upload returns HTTP 413 | larger than 16MB | resize before sending; megaAPI caps `mediaBase64` at 16MB. |
| Audio transcription returns `[audio - transcricao desativada]` | `OPENAI_API_KEY` empty | set the key in `config.py` or accept the fallback (the audio file is still saved under `media/sessionN/`). |

## Tunnel

| Symptom | Cause | Fix |
|---------|-------|-----|
| Quick Tunnel URL changes on every run | by design — Quick Tunnels are ephemeral | switch to a named tunnel (see [SETUP.md § Named Tunnel](SETUP.md#named-tunnel)). |
| Named tunnel returns 502 | service runs as LocalSystem and cannot read user-profile config | edit the service binPath to include `--config "C:\Users\YOU\.cloudflared\config.yml"` (admin PowerShell: `sc.exe config cloudflared binPath= "..."`). |
| Tunnel up but `POST` returns 502 | `ingress.service` set to `http://localhost:3020` and the OS resolves `localhost` to `::1` first | change to `http://127.0.0.1:3020` in `~/.cloudflared/config.yml`. |

## Tests

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pytest` fails on a fresh clone | dependencies missing | `pip install -e .[dev]` (after Task 12 lands `pyproject.toml`). |
| `pytest` fails with `ModuleNotFoundError: config` | the test fixture pre-pop is broken | check `tests/conftest.py` — fixture must inject a fake `config` module before importing the unit under test. |

## Resetting everything

If state is corrupted and you want a clean slate:

```bash
./stop.sh
rm -f messages_session*.jsonl processed_ids_session*.txt raw_debug.jsonl
rm -rf media/
python bootstrap.py
```

`config.py` is preserved.
```

- [ ] **Step 2: Commit**

```bash
git add TROUBLESHOOTING.md
git commit -m "docs: add TROUBLESHOOTING with symptom→fix table"
```

---

## Task 10: CONTRIBUTING.md

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write CONTRIBUTING**

Create `CONTRIBUTING.md`:

```markdown
# Contributing

Thanks for considering a contribution. This project is small enough that you can read the whole codebase in an afternoon — please do, before opening a PR.

## Development setup

```bash
git clone https://github.com/mbkautomacoes/zyon.git
cd Allos
python -m venv .venv
. .venv/Scripts/activate    # Windows
. .venv/bin/activate        # Linux/macOS
pip install -e ".[dev]"
cp config.example.py config.py    # then edit
```

## Tests

```bash
pytest -q                     # full suite
pytest tests/test_xxx.py -v   # single file
pytest -k bootstrap           # by name
```

The CI workflow in `.github/workflows/ci.yml` runs the same suite on every push and PR. A red CI blocks merge.

## Style

- **Python**: standard library only where possible. We avoid runtime deps that are not strictly needed.
- **Tests**: pytest. Use `monkeypatch` for env / `subprocess` / `urllib`. Never hit the real megaAPI in tests.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`. Scope optional (`feat(bootstrap): …`).
- **No emojis** in code, comments, or commit messages.
- **No comments** explaining what code does — only why, when non-obvious.

## Branch and PR flow

1. Open an issue first for non-trivial changes (use the templates in `.github/ISSUE_TEMPLATE/`).
2. Branch off `main`: `git checkout -b feat/your-thing`.
3. TDD where possible. Each commit should leave the suite green.
4. Open a PR. Fill in the template. Link the issue.
5. CI must pass. At least one maintainer review.

## Adding a new feature that touches Claude Code's prompt

`CLAUDE_PROMPT.md` is the source of truth for the agent's runtime contract. If you change it, also:

- Update `PROJETO.md` if the change is architectural.
- Add a test to `tests/test_webhook_parser.py` if you change the JSONL schema.
- Bump `CHANGELOG.md` under `[Unreleased]`.

## Releasing

Maintainers only:

```bash
git checkout main && git pull
# bump CHANGELOG: move [Unreleased] entries under a new version header
git commit -am "chore: release vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main vX.Y.Z
```

Create a GitHub release pointing to the tag with a copy of the CHANGELOG section.
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING (dev setup, tests, commit style, release)"
```

---

## Task 11: GitHub templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Write bug template**

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug report
about: Something does not work as documented
title: "[bug] "
labels: bug
---

**Symptom**

What did you observe? Quote the exact error or describe the misbehavior.

**Expected**

What did you expect to happen instead?

**Reproduction**

1.
2.
3.

**Environment**

- OS:
- Python:
- cloudflared:
- Claude Code CLI:
- Branch / commit:

**`python doctor.py` output**

```
paste here
```

**Logs (`webhook.log`, `cloudflared.log`)**

```
paste relevant lines
```
```

- [ ] **Step 2: Write feature template**

Create `.github/ISSUE_TEMPLATE/feature_request.md`:

```markdown
---
name: Feature request
about: Suggest a capability or improvement
title: "[feat] "
labels: enhancement
---

**Problem**

What pain are you trying to solve? Whose problem is this?

**Proposed solution**

How should it work? Sketch the interface, the user flow, or the API.

**Alternatives**

What did you consider and reject? Why?

**Out of scope**

What this proposal does NOT cover.
```

- [ ] **Step 3: Write PR template**

Create `.github/pull_request_template.md`:

```markdown
## Summary

What does this PR change and why?

## Linked issue

Closes #

## Test plan

- [ ] `pytest -q` is green locally.
- [ ] `python doctor.py` is green against a real deployment OR not applicable.
- [ ] CHANGELOG `[Unreleased]` updated.
- [ ] Docs updated (`README.md` / `SETUP.md` / `TROUBLESHOOTING.md` / `PROJETO.md` / `CLAUDE_PROMPT.md`) if behavior changed.

## Notes for the reviewer

Anything subtle, surprising, or worth knowing.
```

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "chore: add GitHub issue and PR templates"
```

---

## Task 12: CI workflow (pytest on push/PR)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, "trilha-**"]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install pytest
      - name: Stage a fake config for import
        run: |
          cp config.example.py config.py
        shell: bash
      - name: Run pytest
        run: pytest -q
```

- [ ] **Step 2: Verify locally — does pytest still pass after `cp config.example.py config.py` overwrites your real config?**

Skip this check on your dev machine (your real `config.py` would be overwritten). The workflow runs in a fresh CI checkout where `config.py` does not exist, so the `cp` is safe there.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: pytest on ubuntu/windows/macos x py3.10/3.12"
```

---

## Task 13: pyproject.toml (installable as a package)

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write pyproject.toml**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "whatsapp-claude-agent"
version = "1.0.0"
description = "Self-hosted WhatsApp agent powered by Claude Code CLI."
readme = "README.md"
requires-python = ">=3.8"
license = { file = "LICENSE" }
authors = [{ name = "Geovani Junior", email = "sitecasadainfo2011@gmail.com" }]
keywords = ["whatsapp", "claude", "agent", "megaapi", "cloudflared"]
classifiers = [
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3 :: Only",
  "Operating System :: OS Independent",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.urls]
Homepage = "https://github.com/mbkautomacoes/zyon"
Issues = "https://github.com/mbkautomacoes/zyon/issues"
Changelog = "https://github.com/mbkautomacoes/zyon/blob/main/CHANGELOG.md"

[tool.setuptools]
py-modules = [
  "webhook_server",
  "monitor",
  "send_message",
  "media_handler",
  "transcribe",
  "update_webhooks",
  "doctor",
  "add_session",
  "discover_lid",
  "setup_config",
  "bootstrap",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: Verify install**

Run:
```bash
py -m pip install -e ".[dev]"
py -c "import bootstrap; print(bootstrap.extract_quick_tunnel_url('|  https://x-1.trycloudflare.com  |'))"
```
Expected: `https://x-1.trycloudflare.com`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml (PEP 621, editable install)"
```

---

## Task 14: Repo reorg — scripts/ directory

**Why:** Move shell scripts out of the root so the root only contains entrypoints and docs. This is reversible and isolated — no Python import paths change.

**Files:**
- Move: `start.sh`, `start.ps1`, `stop.sh`, `stop.ps1`, `install.sh`, `install.ps1` → `scripts/`
- Modify: `README.md`, `SETUP.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`

- [ ] **Step 1: Create `scripts/` and move files**

Run:
```bash
mkdir -p scripts
git mv start.sh start.ps1 stop.sh stop.ps1 install.sh install.ps1 scripts/
```

- [ ] **Step 2: Update doc references**

For each of `README.md`, `SETUP.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`, replace standalone `./start.sh` with `./scripts/start.sh`, `.\start.ps1` with `.\scripts\start.ps1`, and the same for `stop` and `install`.

Run:
```bash
grep -rn -E "\.(/|\\\\)(start|stop|install)\.(sh|ps1)" README.md SETUP.md TROUBLESHOOTING.md CONTRIBUTING.md
```
Expected: every occurrence is now prefixed with `scripts/` or `scripts\`.

- [ ] **Step 3: Run doctor and pytest**

Run:
```bash
py -m pytest -q
py doctor.py
```
Expected: tests still pass; doctor unaffected (it does not call the scripts).

- [ ] **Step 4: Commit**

```bash
git add scripts/ README.md SETUP.md TROUBLESHOOTING.md CONTRIBUTING.md
git commit -m "chore(repo): move start/stop/install scripts under scripts/"
```

---

## Task 15: Repo reorg — `src/whatsapp_agent/` package

**Why:** Adopt a `src/` layout so imports cannot accidentally resolve to the working directory. Required before publishing as a package.

**This is the riskiest task in the plan.** Move one module at a time, run tests between moves.

**Files:**
- Move: every `*.py` listed in the file-structure table (except `bootstrap.py`, `config*.py`) → `src/whatsapp_agent/`
- Move: `bootstrap.py` → `scripts/bootstrap.py`
- Modify: `tests/conftest.py`, every `tests/test_*.py` import path
- Modify: `pyproject.toml` (replace `py-modules` with `packages`)
- Modify: `README.md`, `SETUP.md`, `TROUBLESHOOTING.md`, `CLAUDE_PROMPT.md` (Python paths)

- [ ] **Step 1: Create the package skeleton**

Run:
```bash
mkdir -p src/whatsapp_agent
touch src/whatsapp_agent/__init__.py
```

Add to `src/whatsapp_agent/__init__.py`:

```python
"""whatsapp_claude_agent — self-hosted WhatsApp agent powered by Claude Code."""
__version__ = "1.0.0"
```

- [ ] **Step 2: Move `update_webhooks.py` first (lowest dependency)**

Run:
```bash
git mv update_webhooks.py src/whatsapp_agent/update_webhooks.py
```

Update `tests/test_update_webhooks.py` — change `import update_webhooks` to:

```python
from whatsapp_agent import update_webhooks
```

Run: `py -m pytest tests/test_update_webhooks.py -v`
Expected: 2 tests pass. (You may need to `pip install -e .` again after the layout shift; do so if pytest cannot find the package.)

Commit:
```bash
git add src/whatsapp_agent/update_webhooks.py tests/test_update_webhooks.py
git commit -m "refactor: move update_webhooks into whatsapp_agent package"
```

- [ ] **Step 3: Move the remaining modules one at a time**

For each of `webhook_server.py`, `monitor.py`, `send_message.py`, `media_handler.py`, `transcribe.py`, `doctor.py`, `add_session.py`, `discover_lid.py`, `setup_config.py`:

```bash
git mv <module>.py src/whatsapp_agent/<module>.py
# update any tests/test_<module>.py: replace `import <module>` with `from whatsapp_agent import <module>`
py -m pytest -q
git add src/ tests/
git commit -m "refactor: move <module> into whatsapp_agent package"
```

If `pytest` fails after a move, fix the imports in the affected test file before moving on. Do not batch.

- [ ] **Step 4: Move `bootstrap.py` to `scripts/`**

```bash
git mv bootstrap.py scripts/bootstrap.py
```

Update `scripts/bootstrap.py` — at the top, after the existing imports, change `subprocess.Popen([sys.executable, "webhook_server.py"], ...)` to `subprocess.Popen([sys.executable, "-m", "whatsapp_agent.webhook_server"], ...)`. Same for the `setup_config.py` and `update_webhooks.py` invocations: use `-m whatsapp_agent.setup_config` and `-m whatsapp_agent.update_webhooks`.

Update `tests/test_bootstrap.py` — change `from bootstrap import …` to:

```python
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "bootstrap",
    pathlib.Path(__file__).parent.parent / "scripts" / "bootstrap.py",
)
bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bootstrap)

extract_quick_tunnel_url = bootstrap.extract_quick_tunnel_url
```

Run: `py -m pytest tests/test_bootstrap.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Update `pyproject.toml`**

Replace the `[tool.setuptools]` block with:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["whatsapp_agent*"]

[project.scripts]
whatsapp-agent-doctor = "whatsapp_agent.doctor:main"
whatsapp-agent-setup = "whatsapp_agent.setup_config:main"
whatsapp-agent-update-webhooks = "whatsapp_agent.update_webhooks:main"
```

Run: `pip install -e ".[dev]"` and `py -m pytest -q`.
Expected: install succeeds, tests pass, the `whatsapp-agent-doctor` console script is on PATH.

- [ ] **Step 6: Update docs**

In `README.md`, `SETUP.md`, `TROUBLESHOOTING.md`, `CLAUDE_PROMPT.md`, replace:

| Old | New |
|-----|-----|
| `python webhook_server.py` | `python -m whatsapp_agent.webhook_server` |
| `python monitor.py N` | `python -m whatsapp_agent.monitor N` |
| `python send_message.py …` | `python -m whatsapp_agent.send_message …` |
| `python doctor.py` | `python -m whatsapp_agent.doctor` (or `whatsapp-agent-doctor` if installed) |
| `python update_webhooks.py` | `python -m whatsapp_agent.update_webhooks` |
| `python bootstrap.py` | `python scripts/bootstrap.py` |

`scripts/start.sh` and `scripts/start.ps1` also need the same `-m` change for `webhook_server` and any path the script writes to (`logs/`, `webhook.log`).

Run: `py -m pytest -q && py -m whatsapp_agent.doctor`
Expected: green tests; doctor shows the same `[OK]` lines as before with the new module path.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "build(reorg): move source under src/whatsapp_agent, expose CLI entrypoints"
```

---

## Task 16: Update `.gitignore` and final smoke

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add new artefacts to `.gitignore`**

Append to `.gitignore`:

```
# Build artefacts
build/
dist/
*.egg-info/

# Bootstrap runtime
cloudflared.log

# IDE
.idea/
*.iml
```

(Verify these are not already present — `grep -n` first.)

- [ ] **Step 2: Final smoke test**

```bash
py -m pytest -q
py -m whatsapp_agent.doctor
```
Expected: tests green; doctor green.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): add build artefacts and cloudflared.log"
```

---

## Task 17: Tag and release notes

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Promote `[Unreleased]` to `[1.1.0]` in CHANGELOG**

Edit `CHANGELOG.md`:

- Move the contents of `## [Unreleased]` under a new heading `## [1.1.0] — YYYY-MM-DD` (use today's date).
- Re-insert an empty `## [Unreleased]` above it.
- Update the link references at the bottom.

- [ ] **Step 2: Commit and tag**

```bash
git add CHANGELOG.md
git commit -m "chore: release v1.1.0 — OSS distribution"
git tag -a v1.1.0 -m "v1.1.0 — OSS distribution: bootstrap.py, cloudflared, src/ layout, CI"
```

- [ ] **Step 3: Push (manual — confirm with the user before running)**

```bash
git push origin trilha-1-multimodal
git push origin v1.1.0
```

Then on GitHub, create a release pointing to `v1.1.0` and paste the `[1.1.0]` section of CHANGELOG as release notes.

---

## Self-Review

**Spec coverage:**

| User requirement | Task |
|------------------|------|
| One-command install | Task 4-5 (bootstrap.py) |
| Quick Tunnel default | Task 5 |
| Named Tunnel as upgrade | Task 8 (SETUP.md § Named Tunnel) |
| Cloudflare Tunnel replaces ngrok in docs | Task 7 (README), Task 8 (SETUP) |
| Auto-push to megaAPI | Task 5 (bootstrap calls update_webhooks) |
| Discover LID auto | Already documented in Task 8; bootstrap leaves it as an explicit step (acceptable — runs once after first message). |
| Polished docs | Tasks 7, 8, 9, 10 |
| OSS license | Task 2 |
| Changelog | Task 3 |
| Contributing guide | Task 10 |
| GitHub templates | Task 11 |
| CI | Task 12 |
| Installable | Task 13 |
| Reorganized layout | Tasks 14, 15 |
| Tag/release | Task 17 |

**Placeholders:** none — every task has concrete code, exact paths, exact commands, expected output.

**Type/method consistency:**
- `extract_quick_tunnel_url` (Task 4) used in Task 5 — name matches.
- `find_cloudflared`, `start_webhook`, `start_quick_tunnel`, `write_public_url`, `push_webhooks`, `main` — defined in Task 5, referenced in Task 15 step 4 — names match.
- `update_webhooks.configure(session_id, instance, token)` — signature matches existing `update_webhooks.py` body.
- `whatsapp_agent` package name consistent across `pyproject.toml`, `tests`, doc updates, and console_scripts.

**Risk callouts (for the executor):**
- Task 15 is the biggest. Move one module at a time and run tests between moves; do not batch.
- Task 12 CI's `cp config.example.py config.py` step assumes `config.example.py` exists at repo root — verify before pushing the workflow (`ls config.example.py`).
- Task 17 step 3 requires the user's explicit approval (push + tag are visible to others).

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-04-28-oss-distribution.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
