# Zyon — WhatsApp Claude Agent

Zyon is a self-hosted WhatsApp agent that uses **Claude Code CLI** as the LLM
engine (no extra API key for the LLM itself). It receives WhatsApp messages
through an HTTP gateway and replies via Claude Code.

The reference WhatsApp gateway is [MBKCHAT](https://mbkchat.com.br) (based on [WuzAPI](https://github.com/asternic/wuzapi)). Zyon is built
to its request/response shape — but the host URL is configurable, and any
backend that mirrors the contract documented in
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) works as a drop-in replacement.
See [Swapping the WhatsApp gateway](#swapping-the-whatsapp-gateway) below.

[![CI](https://github.com/mbkautomacoes/zyon/actions/workflows/ci.yml/badge.svg)](https://github.com/mbkautomacoes/zyon/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Video walkthrough

[![Watch the video](https://img.youtube.com/vi/ZJU_eJV-ENE/maxresdefault.jpg)](https://www.youtube.com/watch?v=ZJU_eJV-ENE)

## TL;DR

```bash
git clone https://github.com/mbkautomacoes/zyon.git zyon
cd zyon
python scripts/bootstrap.py
```

`scripts/bootstrap.py` runs the config wizard, starts the webhook server, opens
a Cloudflare Quick Tunnel, and pushes the public URL to your gateway session.
Then you open Claude Code and paste a one-liner. Done.

## Production deploy (Linux 24/7 — Trilha 2)

For VPS deployment with auto-start on boot, auto-restart on crash, and survival
across SSH disconnects, follow [`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md).
Tested on Ubuntu 24.04 with systemd user services + Cloudflare Named Tunnel +
tmux session running `claude --dangerously-skip-permissions --continue` in a loop.

The agent runs in **headless mode** (`--dangerously-skip-permissions`), since you
interact through WhatsApp and can't approve permission prompts via VPS terminal.
The API phone whitelist is the security boundary; add `CMD_TOKEN` in
`config.py` if you want extra per-message auth.

## Zero-to-running on a fresh machine

Don't have Python / git / curl / cloudflared installed yet? Open Claude Code
in an empty folder and paste the prompt in
[`INSTALL_PROMPT.md`](INSTALL_PROMPT.md). Claude detects your OS, installs
every dependency (winget / brew / apt), clones the repo, and walks you through
the bootstrap.

## Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Python 3.8+ | runtime | https://python.org |
| curl | HTTP calls | bundled on Windows 10+, Linux, macOS |
| cloudflared | public tunnel | `winget install Cloudflare.cloudflared` / `brew install cloudflared` / [docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| Claude Code CLI | the brain | https://docs.anthropic.com/claude-code |
| WhatsApp gateway account | inbound/outbound WhatsApp | [MBKCHAT](https://mbkchat.com.br) (WuzAPI-based) — or any compatible backend, see [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) |
| OpenAI API key (optional) | audio transcription | https://platform.openai.com/api-keys |

> **Model recommendation:** the prompt in `CLAUDE_PROMPT.md` was designed and
> validated against **Anthropic Claude** (Sonnet/Opus). Other models (Kimi,
> GPT-4, etc.) work but tend to add their own instincts (e.g. blocking
> `fromMe:true`, retrying with sanitized text, writing the signature into the
> body). The defenses in `CLAUDE.md` and `send_message.py` make those
> edge-cases safe, but if you want first-try-correct behavior, stick with
> Anthropic Claude.

## Architecture

```
WhatsApp -> gateway -> Cloudflare Tunnel -> webhook_server.py -> messages_sessionN.jsonl
                                                                       |
                                                                       v
WhatsApp <- gateway <- send_message.py <- Claude Code session <- monitor.py (Monitor tool)
```

1. `webhook_server.py` listens on `:3020`, validates the whitelisted phone,
   writes JSONL.
2. `monitor.py N` tails the per-session JSONL — runs **inside** a Claude Code
   session via the Monitor tool.
3. Claude Code reads each JSON line as user input, processes it, and replies
   via `send_message.py`.
4. Cloudflare Tunnel (Quick by default, named tunnel for production) exposes
   `:3020` over HTTPS.

## Two tunnel modes

**Quick Tunnel (default, zero-config):** random `*.trycloudflare.com` URL,
regenerated each run, no domain needed. Used by `scripts/bootstrap.py`.

**Named Tunnel (production):** stable subdomain on a domain you control in
Cloudflare. See [SETUP.md § Named Tunnel](SETUP.md#named-tunnel).

## Multi-session

One deployment can serve multiple WhatsApp instances:

```bash
python -m whatsapp_agent.add_session    # wizard to add session 2, 3, ...
python -m whatsapp_agent.update_webhooks # re-pushes URL to all sessions
```

Open one Claude Code session per WhatsApp session and paste:
`Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: <N>`

## Multimodal

| Direction | Text | Image | Audio | Video |
|-----------|------|-------|-------|-------|
| Receive | yes | yes (Claude reads natively) | yes (Whisper, optional) | rejected |
| Send | yes | yes (`send_message.py --type image`) | no | no |

## Swapping the WhatsApp gateway

Zyon was built against [MBKCHAT](https://mbkchat.com.br) (WuzAPI-based), but the host URL is a
runtime config value, not hardcoded. Any backend that implements the contract
in [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) — same endpoints, same JSON
payloads, same `token:` header — drops in by changing one
field.

**To switch gateways** (whether to a different WuzAPI host, a self-hosted
WuzAPI instance, or any compatible backend):

1. Re-run the wizard with `rm config.py && python -m whatsapp_agent.setup_config`.
2. Enter the new `API base URL` when prompted.
3. Run `python -m whatsapp_agent.update_webhooks` to push the public webhook
   URL to the new instance.

**Where the gateway is referenced in the code** (in case you need to adapt to
a backend that's almost-but-not-quite WuzAPI-shaped):

| File | What it does |
|------|--------------|
| `src/whatsapp_agent/send_message.py` lines 20-21 | Outbound text + image endpoints (`/chat/send/text`, `/chat/send/image`). |
| `src/whatsapp_agent/send_message.py` lines 66-111 | Outbound JSON payloads for text and image. |
| `src/whatsapp_agent/update_webhooks.py` line 32 | Webhook config endpoint (`/webhook`). |
| `src/whatsapp_agent/media_handler.py` line 93 | Media download endpoint (`/chat/downloadimage`). |
| `src/whatsapp_agent/webhook_server.py` lines 72-131 | Inbound payload parser — field names the gateway must produce (`data.chat`, `data.fromMe`, `data.message.conversation`, `data.message.imageMessage.{base64,caption,mimeType}`, etc.). |
| `src/whatsapp_agent/doctor.py` lines 115-135 | Health-check endpoint (`/session/status`). |

If your gateway uses different paths or payload shapes, edit those locations.
Everything else (whitelist, JSONL queue, monitor, signature handling) is
gateway-agnostic.

## Persistent task memory (beads)

Zyon uses [beads](https://github.com/gastownhall/beads) to maintain a
dependency-aware task graph that survives session restarts. `bootstrap.py`
installs and initializes it automatically on Linux/macOS; on Windows install
the binary manually from the beads releases page.

How Claude Code uses it (full rules in [CLAUDE.md](CLAUDE.md)):

- `bd ready --json` to find work that has no open blockers.
- `bd create "Title" -p 1` to log a new task.
- `bd update <id> --claim` to atomically take ownership.
- `bd close <id> "what was done"` to finish.

The database lives in `.beads/` (gitignored).

## Repo layout

```
.
|-- src/whatsapp_agent/   # installable package (pip install -e .)
|   |-- webhook_server.py # HTTP :3020 receiver (gateway-shape parser)
|   |-- monitor.py        # JSONL tail (Monitor target)
|   |-- send_message.py   # outbound gateway client (text + image)
|   |-- update_webhooks.py# push PUBLIC_WEBHOOK_URL to all sessions
|   |-- doctor.py         # diagnostics
|   |-- add_session.py    # wizard to add another WhatsApp session
|   |-- discover_lid.py   # auto-fill LID after first message
|   |-- media_handler.py  # decrypt+save media via gateway
|   |-- transcribe.py     # OpenAI Whisper wrapper
|   `-- setup_config.py   # interactive config wizard
|-- scripts/
|   |-- bootstrap.py      # one-command install/run
|   |-- start.{sh,ps1}    # start webhook only (tunnel manages itself)
|   `-- stop.{sh,ps1}     # stop webhook
|-- config.example.py     # template (copy to config.py — gitignored)
|-- tests/                # pytest
|-- docs/                 # extended docs and roadmaps
|   |-- API_CONTRACT.md   # gateway contract (auth + endpoints + payloads)
|   `-- plans/            # design plans
|-- CLAUDE_PROMPT.md      # paste into Claude Code to activate the agent
|-- INSTALL_PROMPT.md     # zero-to-running prompt for fresh machines
|-- SETUP.md              # step-by-step walkthrough (gateway signup, tunnel modes)
|-- TROUBLESHOOTING.md    # symptom -> fix
|-- CONTRIBUTING.md
|-- CHANGELOG.md
`-- LICENSE               # MIT
```

## Documentation

- **[SETUP.md](SETUP.md)** — full walkthrough including gateway account creation and named tunnel.
- **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)** — HTTP contract a gateway backend must implement.
- **[INSTALL_PROMPT.md](INSTALL_PROMPT.md)** — zero-to-running prompt for fresh machines.
- **[CLAUDE_PROMPT.md](CLAUDE_PROMPT.md)** — the prompt that activates the agent inside Claude Code.
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — common boot/runtime issues.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — dev setup, test commands, commit style.
- **[CHANGELOG.md](CHANGELOG.md)** — release history.

## Security

- `config.py` is **gitignored** — your tokens never leave your machine.
- Whitelist by phone number — only your authorized number(s) trigger the agent.
- Loop guard via `*Claude Code*` signature — the agent never replies to its own messages.
- Self-chat is supported (sending to yourself).

## License

MIT — see [LICENSE](LICENSE).

## Status

- Tag `v1.2.0` (2026-05-09) — Trilha 2 promoted to official production path. Canonical 24/7 runbook: [`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md). `webhook_server.py` exposes `GET /healthz`. `--dangerously-skip-permissions` is mandatory for VPS mode.
- Trilha 3 (Docker OSS) was attempted and **abandoned** (commit `eaccb6f`) — `claude --continue` runs in Agent SDK headless mode and does not expose the Monitor tool this project depends on. See CHANGELOG for details.
- Trilha 1 (local dev) — multi-session + multimodal validated end-to-end on 2026-04-28; remains the quick-start path via `python scripts/bootstrap.py`.
- Tunnel migrated from ngrok to Cloudflare Tunnel (Quick Tunnel for dev, Named Tunnel for production).
