# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] — 2026-05-09

### Added
- **Trilha 2 promoted to official production path.** `docs/DEPLOY_24_7_LINUX.md` is now the canonical 24/7 runbook (tested on Ubuntu 24.04). It uses three systemd **user** services — `zyon-webhook.service`, `zyon-tunnel.service`, `zyon-monitor.service` — plus a tmux session running `claude --dangerously-skip-permissions --continue` in a loop, and a Cloudflare Named Tunnel for a stable public URL.
- `webhook_server.py` now exposes `GET /healthz` returning JSON `{ "status": "ok", "sessions": [...] }` — curl-friendly healthcheck for Cloudflare and external monitoring.
- `--dangerously-skip-permissions` is now documented as **mandatory** for the production (VPS) flow, since the operator interacts via WhatsApp and cannot approve permission prompts on a remote terminal. The megaAPI phone whitelist (and optional `CMD_TOKEN`) remain the security boundary.

### Removed
- **Trilha 3 (Docker OSS distribution) abandoned.** Root cause: `claude --continue` launched non-interactively (the only way to keep `claude` alive inside a container) runs in the Agent SDK headless mode, which does **not** expose the Monitor tool that this project depends on. Tested 8 model + gateway combinations — all failed for the same structural reason. Reverted in commit `eaccb6f`. Files removed: `docker/`, `docker-compose*.yml`, `scripts/docker_setup.py`, `docs/DOCKER.md`, `docs/plans/2026-05-07-trilha-3-docker-oss.md`, `tests/test_agent_loop.py`, `tests/test_docker_compose.py`, `tests/test_dockerfile_webhook.py`, `tests/test_zz_healthz.py`, `.dockerignore`, `.env.example`. The official 24/7 path is Trilha 2 (systemd + tmux on a Linux host).

## [1.1.1] — 2026-04-29

### Fixed
- `bootstrap.py` now passes `--config nul` (Windows) / `--config /dev/null` (POSIX) when starting the Quick Tunnel, so a pre-existing `~/.cloudflared/config.yml` from a named-tunnel install does not hijack the Quick Tunnel routing with HTTP 404. (Discovered during fresh-clone Allos-test validation on a host that already had `allos.dev-junior.com` configured.)
- Wizard `setup_config.py` post-install instructions refreshed for the post-Task-15 layout (`python scripts/bootstrap.py`, `python -m whatsapp_agent.discover_lid`, etc.) — replaces the obsolete `start.ps1` / `python discover_lid.py` references.
- `send_message.py` strips any pre-existing `*Claude Code*` signature from the body before appending — prevents duplicated signatures when the agent (e.g. on non-Anthropic models) writes the signature into the reply text. Covered by tests.
- Prompt rules: `fromMe` is now explicitly stated as **not** a filter — the only loop guard is the `*Claude Code*` text signature. Self-chat is the default use case; `fromMe: true` must be processed.
- Prompt rules: `send_message` must be called exactly once per user message — no automatic retry with sanitized text. Strip emojis / non-BMP characters before the single call instead.

### Added
- README explicitly notes that the prompt was designed and validated against Anthropic Claude (Sonnet/Opus). Other models (Kimi, GPT-4) work because of the rules in CLAUDE.md and the `send_message` defense, but Anthropic Claude is the canonical choice for first-try-correct behavior.
- `TROUBLESHOOTING.md` covers four new real-world scenarios captured during Allos-test / Allos3 validation:
  1. Quick Tunnel returns 404 because of an inherited `~/.cloudflared/config.yml`.
  2. Stale `monitor.py` from a previous Claude Code session in another folder silently consumes JSONL of the wrong project.
  3. Wizard accepted an instance whose connected phone does not match `ALLOWED_PHONE` (validation gap).
  4. Spam / newsletter traffic from a megaAPI instance whose webhook still points at this tunnel.

## [1.1.0] — 2026-04-29

### Added
- Beads (`bd`) integration for persistent task memory: auto-installed and initialized by `bootstrap.py`, documented in `CLAUDE.md` and `TROUBLESHOOTING.md`.
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

[Unreleased]: https://github.com/mbkautomacoes/zyon/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/mbkautomacoes/zyon/releases/tag/v1.2.0
[1.1.1]: https://github.com/mbkautomacoes/zyon/releases/tag/v1.1.1
[1.1.0]: https://github.com/mbkautomacoes/zyon/releases/tag/v1.1.0
[1.0.0-trilha1]: https://github.com/mbkautomacoes/zyon/releases/tag/v1.0-trilha1
