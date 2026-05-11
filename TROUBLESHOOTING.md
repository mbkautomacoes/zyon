# Troubleshooting

When in doubt, run `python -m whatsapp_agent.doctor` first. It prints the state of every component.

## Boot

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bootstrap.py` exits "ERROR: cloudflared not found" | binary not on PATH | `winget install Cloudflare.cloudflared` (Windows), `brew install cloudflared` (macOS), or download from Cloudflare. |
| `bootstrap.py` exits "ERROR: cloudflared did not print a Quick Tunnel URL" | Cloudflare blocked the run, or the network has outbound QUIC blocked | check `cloudflared.log` for the real error. Re-run with `cloudflared tunnel --url http://127.0.0.1:3020 --protocol http2` if QUIC is blocked. |
| `webhook_server.py` exits immediately | `:3020` is in use | `lsof -iTCP:3020 -sTCP:LISTEN` (Linux/macOS) or `netstat -ano \| findstr :3020` (Windows) — kill the offending process. |
| `setup_config.py` runs every time | `config.py` was deleted or never written | run `python -m whatsapp_agent.setup_config` once and verify the file lands in the project root. |

## megaAPI

| Symptom | Cause | Fix |
|---------|-------|-----|
| `doctor.py` reports `megaAPI sessao N: HTTP 404` | wrong instance name | check the instance string in `config.py` matches the megaAPI dashboard. |
| `doctor.py` reports `megaAPI sessao N: HTTP 401` | bad token | regenerate the token in the megaAPI dashboard, update `config.py`, run `python -m whatsapp_agent.update_webhooks`. |
| Webhook never fires | URL not registered or instance disconnected | run `python -m whatsapp_agent.update_webhooks`; verify the WhatsApp connection in the megaAPI dashboard. |
| Wizard accepted any instance name and webhook never fires | the instance you typed is not the one connected to your authorized phone (e.g. typed `Projeto3` when the connected number lives under `Projeto2`) | confirm with `curl -s -H "Authorization: Bearer <TOKEN>" "https://apibusiness1.megaapi.com.br/rest/instance/<INSTANCE>"` — the returned `instance.user.id` must match `ALLOWED_PHONE` in `config.py`. If it doesn't, edit `config.py` and re-run `python -m whatsapp_agent.update_webhooks`. |
| Outbound `send_message.py` returns `error code: 502` | transient megaAPI / upstream Cloudflare hiccup | retry once; if it persists, check the megaAPI status page. The instance is fine — `send_message.py` does not retry, so a transient 502 means the message simply did not go out. |

## Runtime

| Symptom | Cause | Fix |
|---------|-------|-----|
| Message arrives in JSONL but Claude does not reply | no Claude Code session has the Monitor tool active on `python -m whatsapp_agent.monitor N` | open a Claude Code session and paste `Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: N`. |
| Two replies for one message | duplicate `monitor.py` processes | `ps -ef \| grep whatsapp_agent.monitor \| grep -v grep` — kill all but one. |
| `monitor.py` runs but messages are silently dropped | `monitor.py` was launched standalone (nohup/&) — its stdout has no consumer; it marks every message as processed | kill it (`pkill -f "whatsapp_agent.monitor"`), then activate it inside a Claude Code session via the Monitor tool. |
| Messages reach `messages_session1.jsonl` but `processed_ids_session1.txt` stays empty AND no reply appears on WhatsApp | a `monitor.py` process from a previous Claude Code session in a different folder is still alive — its working directory points at another project's JSONL, so it never sees this project's messages | Windows: `powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" \| Where-Object { $_.CommandLine -like '*whatsapp_agent.monitor*' } \| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"`. Linux/macOS: `pkill -f whatsapp_agent.monitor`. Then close the stale Claude Code session, open a new one **inside the project folder you actually want to monitor**, and re-paste the activation prompt — the Monitor tool will spawn a fresh `monitor.py` with the correct cwd. |
| Webhook receives messages from a megaAPI instance you did NOT configure (e.g. spam / newsletters) | another instance under the same megaAPI account has its webhook URL pointing at this tunnel | open the megaAPI dashboard for the spam-source instance and either point its webhook elsewhere or disable it: `curl -s -X POST "https://apibusiness1.megaapi.com.br/rest/webhook/<INSTANCE>/configWebhook" -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"messageData":{"webhookUrl":"","webhookEnabled":false}}'`. |
| Replies loop infinitely | the loop guard signature `*Claude Code*` was removed from outgoing messages | restore `SIGNATURE = "*Claude Code*"` in `config.py`. |
| Image upload returns HTTP 413 | larger than 16MB | resize before sending; megaAPI caps `mediaBase64` at 16MB. |
| Audio transcription returns `[audio - transcricao desativada]` | `OPENAI_API_KEY` empty | set the key in `config.py` or accept the fallback (the audio file is still saved under `media/sessionN/`). |

## Tunnel

| Symptom | Cause | Fix |
|---------|-------|-----|
| Quick Tunnel URL changes on every run | by design — Quick Tunnels are ephemeral | switch to a named tunnel (see [SETUP.md § Named Tunnel](SETUP.md#named-tunnel)). |
| Named tunnel returns 502 | service runs as LocalSystem and cannot read user-profile config | edit the service binPath to include `--config "C:\Users\YOU\.cloudflared\config.yml"` (admin PowerShell: `sc.exe config cloudflared binPath= "..."`). |
| Tunnel up but `POST` returns 502 | `ingress.service` set to `http://localhost:3020` and the OS resolves `localhost` to `::1` first | change to `http://127.0.0.1:3020` in `~/.cloudflared/config.yml`. |
| Quick Tunnel returns HTTP 404 for any request even though `cloudflared` is running and printed a `*.trycloudflare.com` URL | host already had a `~/.cloudflared/config.yml` from a previous named-tunnel install. cloudflared loads it automatically and its `ingress` rules hijack the Quick Tunnel routing — any Host header that does not match the named tunnel hostname falls through to the `http_status:404` fallback. | `bootstrap.py` already handles this by passing `--config nul` (Windows) / `--config /dev/null` (POSIX). If you start cloudflared by hand, do the same: `cloudflared tunnel --no-autoupdate --config nul --url http://127.0.0.1:3020`. |
| `cloudflared.log` shows `failed to request quick Tunnel: ... context deadline exceeded` | transient network issue or Cloudflare API momentarily unreachable | re-run `python scripts/bootstrap.py` — the wizard and bd init are idempotent so it picks up where it left off. |

## Tests

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pytest` fails on a fresh clone | dependencies missing | `pip install -e .[dev]` (after Task 12 lands `pyproject.toml`). |
| `pytest` fails with `ModuleNotFoundError: config` | the test fixture pre-pop is broken | check `tests/conftest.py` — fixture must inject a fake `config` module before importing the unit under test. |

## VPS / Linux 24/7 (Trilha 2)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bash: ./scripts/start.sh: /bin/bash^M: bad interpreter` on Linux after cloning from Windows | files committed with CRLF line endings; Linux loader chokes on the trailing `\r` | `sed -i 's/\r$//' scripts/*.sh` (or globally `find . -name "*.sh" -exec sed -i 's/\r$//' {} +`). To prevent recurrence, ensure `.gitattributes` declares `*.sh text eol=lf`. |
| Quick Tunnel URL changed after VPS reboot and WhatsApp messages stop arriving | Quick Tunnel is ephemeral by design; production needs a Named Tunnel | switch to a Named Tunnel as documented in [`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md). The named tunnel keeps the same subdomain across restarts. |
| `claude` in the tmux loop sits at the "Sign in" screen forever | first-time auth was never completed under the user that owns the systemd unit | attach the tmux session (`tmux attach -t zyon`), run `claude /login` interactively once, finish the browser/device flow, then detach with `Ctrl-b d`. After the first successful login the credential is cached under `~/.claude/` for that user and `--continue` works headlessly. |
| `claude --continue` exits immediately under the systemd user service with "permission prompt" or "approval pending" output | `--dangerously-skip-permissions` was not passed | edit `scripts/claude_monitor_loop.sh` (or the equivalent wrapper) so `claude` is launched with `--dangerously-skip-permissions --continue`. This flag is **mandatory** for VPS mode — the operator is on WhatsApp and cannot approve prompts. |
| `claude` cannot read/write `~/.claude/projects/...` when launched by systemd user service | the directory was created by another user (e.g. root during initial test) and the unit user lacks read/write | `sudo chown -R <unit-user>:<unit-user> ~<unit-user>/.claude` and re-enable lingering with `sudo loginctl enable-linger <unit-user>`. |
| `curl https://agent.your-domain.com/healthz` returns 502 | webhook not running, or cloudflared is up but cannot reach `127.0.0.1:3020` | `systemctl --user status zyon-webhook.service` then `journalctl --user -u zyon-webhook -n 50`. Check `ingress.service` in `~/.cloudflared/config.yml` is `http://127.0.0.1:3020` (not `localhost`, which can resolve to `::1`). |
| `curl https://agent.your-domain.com/healthz` returns 200 but WhatsApp replies never come | webhook receives but no Claude Code session has the Monitor tool active | `tmux attach -t zyon` and check the `claude` instance is on the agent prompt and Monitor is engaged; if not, restart `zyon-monitor.service` and re-cole the prompt. |

## Beads (bd)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bd: command not found` after bootstrap | install one-liner failed (network / proxy / curl missing) | re-run `bash <(curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh)` manually, or install from https://github.com/gastownhall/beads/releases. |
| `bd init` says "already initialized" | `.beads/` already exists | expected — beads is idempotent. Use `bd ready --json` to inspect existing tasks. |
| Tasks disappear between sessions | running `bd` from a different cwd | always run `bd` from the repo root (where `.beads/` lives), or set `BEADS_DIR=/path/to/repo/.beads`. |

## Resetting everything

If state is corrupted and you want a clean slate:

```bash
./scripts/stop.sh
rm -f messages_session*.jsonl processed_ids_session*.txt raw_debug.jsonl
rm -rf media/
python scripts/bootstrap.py
```

`config.py` is preserved.
