# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Every rule below is **default behavior** for any session — it can be overridden by an explicit user instruction in the session.

## Architecture

Zyon bridges WhatsApp ↔ Claude Code. Data flow:

```
WhatsApp → MBKCHAT/WuzAPI → Cloudflare Tunnel → webhook_server.py (:3020)
  → messages_sessionN.jsonl → monitor.py (Monitor tool in Claude Code)
  → Claude Code processes → send_message.py → MBKCHAT/WuzAPI → WhatsApp
```

**Key modules** (`src/whatsapp_agent/`):
- `webhook_server.py` — HTTP server on `:3020`; validates phone whitelist, parses media, appends JSONL lines; also serves `GET /healthz` returning JSON `{"status":"ok","sessions":[...]}` for Cloudflare and external monitoring
- `monitor.py` — tails `messages_sessionN.jsonl`; maintains `processed_ids_sessionN.txt`; filters own messages by signature
- `send_message.py` — outbound API client (MBKCHAT/WuzAPI); auto-appends `*Claude Code*` signature
- `media_handler.py` — handles media from webhook base64 or API download; saves to `media/sessionN/`
- `transcribe.py` — wraps OpenAI Whisper for audio; returns bracketed fallback if key missing
- `doctor.py` — diagnostics: Python, curl, cloudflared, config, webhook port, tunnel, API creds
- `bootstrap.py` — one-command setup: config wizard → webhook server → Quick Tunnel → update webhooks
- `trends_agent.py` — Google Trends BR subagent; uses `agent-browser` (npm) to scrape trends.google.com

**Multi-session:** each Claude Code session monitors exactly one WhatsApp session. Webhook multiplexes via `?session=N` query param. Add sessions with `python -m whatsapp_agent.add_session`.

## Commands

```bash
# Tests (run after any edit to src/)
python -m pytest -q
python -m pytest tests/test_send_message.py -q  # single file

# Diagnostics
python -m whatsapp_agent.doctor

# Start background services (webhook + tunnel)
.\scripts\start.ps1          # Windows
./scripts/start.sh           # Linux/Mac

# Bootstrap (first-time setup)
python scripts/bootstrap.py

# Re-register webhook URL with API (after tunnel URL change or config edit)
python -m whatsapp_agent.update_webhooks

# Discover LID after first message arrives on a new session
python -m whatsapp_agent.discover_lid [N]

# Session close
git pull --rebase && bd dolt push && git push
```

## Rule 1 — when this session is acting as the WhatsApp agent

When this Claude Code session has an active Monitor tool watching `python -m whatsapp_agent.monitor N`, you are operating as the WhatsApp agent for session `N`. In that role:

- **Always** reply by calling `python -m whatsapp_agent.send_message <from> "<reply text>" <N>` (or `--type image <from> <path> "<caption>" <N>` for images). Use the `from` field of the JSONL message.
- **Call `send_message` exactly once per user message.** If the first call errors, read stderr, fix root cause, call once more (failed call did not deliver). Never retry "with a sanitized version" — the user receives two messages.
- **Never type `*Claude Code*` into the reply text.** `send_message.py` appends it automatically; writing it manually duplicates the signature.
- **Strip emojis / non-BMP characters** before calling `send_message` if Windows shell rejects them — edit before sending, do not send twice.
- **Never answer inline in the CLI.** The end user is on WhatsApp; CLI text is invisible to them.
- Split replies over ~4000 chars into multiple `send_message` calls preserving order.
- On error, always send a short WhatsApp reply ("Erro ao processar — tente reformular") in addition to logging in CLI.

When **not** acting as the WhatsApp agent (no Monitor tool active), reply normally in the CLI.

### Self-chat is the default use case — `fromMe` is NOT a filter

Every legitimate user message in self-chat mode arrives with `fromMe: true`. **DO NOT ignore those messages.**

The single loop-guard criterion is the literal string `*Claude Code*` in the text field. The webhook already applied the phone whitelist; if a JSONL line exists, it is authorized — process it unless text contains `*Claude Code*`.

## Rule 2 — persistent task memory via beads (`bd`)

The database lives in `.beads/`. Beads survives across sessions; markdown TODO lists do not.

- Check `.beads/` exists before `bd init` — do not re-init.
- Run `bd ready --json` before creating tasks to avoid duplicates.
- `bd create "Title" -p 0|1|2` (0=critical, 1=important, 2=nice-to-have)
- Claim before starting: `bd update <id> --claim`
- Close with reason: `bd close <id> "what was done (commit SHA, file path)"`
- Use `--json` when piping to another tool.
- Use beads for cross-session work; use in-session TodoWrite only for ephemeral bookkeeping.

**Session close (mandatory):**
```bash
git pull --rebase
bd dolt push
git push
git status  # must show "up to date with origin"
```

## Rule 3 — runtime hygiene

- Always invoke modules as `python -m whatsapp_agent.<module>` — never `python <module>.py`.
- The webhook server, Cloudflare Tunnel, and `monitor.py` instances are long-running. **Do not kill them** unless the user explicitly asks. Check liveness with `ps -ef | grep ...` or `doctor`.
- `monitor.py` MUST be launched via Claude Code's Monitor tool, never via `nohup`/`&`/`run_in_background`. Standalone monitors silently consume messages (mark processed_ids with no reader).
- After edits to `src/whatsapp_agent/`, run `python -m pytest -q` before claiming done.
- After edits to `config.py` or `PUBLIC_WEBHOOK_URL`, run `python -m whatsapp_agent.update_webhooks`.

## Rule 4 — secrets

- `config.py` is gitignored and contains live tokens (`API_TOKEN`, `OPENAI_API_KEY`). Never stage it or cat its contents into a chat or commit message.
- `config.example.py` is the public template; keep variable names + comments in sync with `config.py`, never actual values.

## Rule 5 — when in doubt, run the doctor

`python -m whatsapp_agent.doctor` is the single command that tells you whether the system is healthy. Run it at the start of any debugging session and before changing code when a user reports something is wrong.

For a remote / production check (no shell on the host), `curl https://<your-tunnel>/healthz` returns `{"status":"ok","sessions":[...]}` if the webhook is up.

## Rule 6 — production (24/7) deploy path

The official 24/7 deploy is **Trilha 2**: Linux host (tested Ubuntu 24.04), three systemd **user** services (`zyon-webhook.service`, `zyon-tunnel.service`, `zyon-monitor.service`), Cloudflare Named Tunnel, and a tmux session running `claude --dangerously-skip-permissions --continue` in a loop. Canonical runbook: [`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md).

`--dangerously-skip-permissions` is **mandatory** in VPS mode — the operator interacts via WhatsApp and cannot approve permission prompts on a remote terminal. The API phone whitelist (and optional `CMD_TOKEN`) remain the security boundary.

Trilha 3 (Docker OSS distribution) was attempted in May 2026 and **abandoned** in commit `eaccb6f` (tag `v1.2.0`). Root cause: `claude --continue` launched non-interactively runs in Agent SDK headless mode, which does not expose the Monitor tool. Do not reintroduce a Docker stack without solving that first.
