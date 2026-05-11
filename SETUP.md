# Setup walkthrough

This is the slow path. If you just want to try the agent, follow the
[README TL;DR](README.md#tldr) instead.

## 1. Create a megaAPI account and instance

1. Sign up at https://megaapi.io.
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
python scripts/bootstrap.py
```

`scripts/bootstrap.py` will:

1. Verify Python, curl, and cloudflared are present.
2. Run the config wizard if `config.py` does not exist (asks for instance, token, phone, optional OpenAI key).
3. Start `webhook_server.py` on `:3020`.
4. Open a Cloudflare Quick Tunnel and capture the public URL.
5. Write `PUBLIC_WEBHOOK_URL` into `config.py`.
6. Run `update_webhooks.py` to push the URL to every megaAPI session.
7. Print a "READY" banner with the URL and the next step.
8. Install beads (`bd`) and run `bd init` in the project root if not already present (skipped on Windows — install manually from the beads releases page if you want persistent task memory).

## 4. Discover your LID

Send any WhatsApp message to your own number. Then run:

```bash
python -m whatsapp_agent.discover_lid
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

Claude will read the prompt, run `python -m whatsapp_agent.doctor`, activate the Monitor tool on `python -m whatsapp_agent.monitor 1`, and start replying to incoming WhatsApp messages.

## 6. Test it

Send any text message to your WhatsApp number. Claude replies within seconds, signed `*Claude Code*`.

## Multi-session

Add another WhatsApp instance:

```bash
python -m whatsapp_agent.add_session        # asks for instance/token/phone, assigns next ID
python -m whatsapp_agent.update_webhooks    # re-pushes PUBLIC_WEBHOOK_URL to all sessions
```

Open a second Claude Code session in another terminal and paste:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 2
```

Each Claude Code session monitors **exactly one** WhatsApp session.

## Named Tunnel (production)

Quick Tunnel URLs are random and regenerate on every restart. For a stable URL, switch to a Cloudflare Named Tunnel.

Quick reference (Windows / macOS dev box):

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

Update `config.PUBLIC_WEBHOOK_URL` to `https://agent.your-domain.com` and run `python -m whatsapp_agent.update_webhooks`.

Run the tunnel as a background service:

```bash
# Windows (admin PowerShell):
cloudflared service install
```

## Linux 24/7 production (VPS) — Trilha 2

For a real production deploy on a Linux box (auto-start on boot, auto-restart on crash, survives SSH disconnect, stable subdomain), follow the canonical runbook:

**[`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md)** — tested on Ubuntu 24.04. It walks through three systemd **user** services (`zyon-webhook.service`, `zyon-tunnel.service`, `zyon-monitor.service`), a tmux session running `claude --dangerously-skip-permissions --continue` in a loop, and a Cloudflare Named Tunnel.

`--dangerously-skip-permissions` is **mandatory** for the VPS flow — you interact via WhatsApp and cannot approve permission prompts on a remote terminal. The megaAPI phone whitelist (and optional `CMD_TOKEN` in `config.py`) remain the security boundary.

You can sanity-check the running webhook from any host with:

```bash
curl https://agent.your-domain.com/healthz
# {"status": "ok", "sessions": ["1", ...]}
```

## Stopping

```bash
./scripts/stop.sh        # Linux/macOS
.\scripts\stop.ps1       # Windows
```

This stops the webhook. The Cloudflare Tunnel is managed separately (Quick Tunnel exits when the spawning shell does; named tunnel runs as a service).

## Diagnostics

```bash
python -m whatsapp_agent.doctor
```

Prints `[OK]` / `[WARN]` / `[ERRO]` for each component. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes.
