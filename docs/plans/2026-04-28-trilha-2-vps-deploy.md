# Trilha 2 — VPS Deploy Implementation Plan

> **STATUS — SUPERSEDED (2026-05-09, tag `v1.2.0`).** Trilha 2 shipped, but the as-built design diverged from this plan: **systemd user services** (not system units under a dedicated `whatsapp` account), no `/opt/whatsapp-claude-agent` install root, no `install/deploy_vps.sh` orchestrator, no `install/` shim layout, and no Docker dry-run. The canonical, as-shipped runbook is **[`docs/DEPLOY_24_7_LINUX.md`](../DEPLOY_24_7_LINUX.md)**. This file is kept for historical context (design rationale, Task 1 healthz endpoint which did land, etc.) — do not execute it as written.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mover o agente WhatsApp Claude Agent de localhost (Windows + ngrok + Claude Code interativo) para VPS Linux operando 24/7 com Cloudflare Tunnel + systemd + tmux.

**Architecture:**
- **Tunnel:** ngrok substituído por Cloudflare Tunnel (URL fixa, TLS automático, sem expor porta).
- **Process supervision:** systemd cuida de `webhook_server.py` e `cloudflared` (auto-restart, logs via journalctl).
- **Claude Code 24/7:** sessão `tmux` persistente roda `claude` com prompt do `CLAUDE_PROMPT.md` carregado uma vez. Auto-attach via `tmux attach -t whatsapp` pra debug.
- **Bootstrap:** `install/deploy_vps.sh` provisiona VPS Ubuntu/Debian limpo de ponta a ponta, idempotente.
- **Healthcheck:** `webhook_server.py` ganha endpoint `GET /healthz` pra Cloudflare + monitoring externo.
- **Compat:** Trilha 1 (localhost/Windows) continua intacta. Scripts antigos na raiz ficam como shims chamando `install/`.

**Tech Stack:**
- Python 3.10+ stdlib (já em uso)
- Bash (deploy scripts)
- systemd (process supervision)
- cloudflared (Cloudflare Tunnel)
- tmux (Claude Code persistente)
- Ubuntu 22.04 LTS / Debian 12 (testado nessas distros)
- pytest (unit tests do healthz endpoint)

**Out of scope:**
- Migrar TTS / vídeo (cortado da Trilha 1, segue cortado).
- Headless Claude Code via systemd unit (requer investigação de auth não-interativa, postergado).
- Worker queue / fila Redis (arquitetura alternativa, postergada).
- Trocar Claude Code por Anthropic API direta (fallback de emergência, documentado mas não implementado).
- Multi-tenancy (1 deploy = 1 usuário; multi-instância já existente via SESSIONS).

**Decisão chave:** Adotamos **Opção A (tmux)** do roadmap. Justificativa: zero custo, zero refactor de Claude Code, debug facilitado por `tmux attach`. Risco aceito: reboot do VPS exige `systemd unit` que faz `tmux new-session -d` → `claude` → cola prompt; auth Claude Code precisa estar pré-configurada (não headless puro).

---

## File Structure

**Novos arquivos:**
- `install/deploy_vps.sh` — bootstrap idempotente VPS Ubuntu/Debian
- `install/start_claude_tmux.sh` — sobe sessão tmux com Claude Code carregado
- `install/cloudflared_setup.sh` — registra tunnel CF e gera config
- `systemd/webhook.service` — unit pro webhook_server.py
- `systemd/cloudflared.service` — unit pro cloudflared (se não vier do pacote oficial)
- `systemd/whatsapp-tmux.service` — unit pra subir tmux com Claude Code no boot
- `docs/VPS_OPERATIONS.md` — runbook (deploy, restart, logs, backup, troubleshoot)
- `tests/test_healthz.py` — unit test do endpoint /healthz

**Modificados:**
- `webhook_server.py` — adicionar handler GET `/healthz`
- `doctor.py` — adicionar `check_vps_mode()` (detecta systemd, valida units, checa tmux)
- `CLAUDE_PROMPT.md` — adicionar seção "Modo VPS" com instruções específicas
- `README.md` — link pra VPS_OPERATIONS.md, atualizar status Trilha 2
- `PROJETO.md` — marcar Trilha 2 como concluída quando finalizar
- `.gitignore` — adicionar `cloudflared-config.yml`, `*.pem`, `tunnel-*.json` (credenciais CF)

**Movidos (preservando compat):**
- `install.ps1` raiz → `install/install.ps1` (raiz vira shim 1-linha)
- `install.sh` raiz → `install/install.sh` (raiz vira shim 1-linha)

**Não tocados:**
- `monitor.py`, `send_message.py`, `media_handler.py`, `transcribe.py`, `add_session.py`, `setup_config.py`, `discover_lid.py` — Trilha 1 funcional, sem mudança.
- `start.{ps1,sh}`, `stop.{ps1,sh}` — uso localhost só, mantém raiz.

---

## Task 1: Healthcheck endpoint /healthz no webhook

**Files:**
- Modify: `webhook_server.py` (adicionar handler GET)
- Create: `tests/test_healthz.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for /healthz endpoint."""
import json
import sys
import threading
import time
from urllib.request import urlopen


def _import_ws():
    sys.modules.pop("webhook_server", None)
    import webhook_server
    return webhook_server


def test_healthz_returns_200_json(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)

    # Build a mock request that exercises do_GET on /healthz
    captured = {}

    class FakeWFile:
        def __init__(self): self.buf = b""
        def write(self, b):  self.buf += b

    handler.path = "/healthz"
    handler.wfile = FakeWFile()
    handler.send_response = lambda code: captured.setdefault("status", code)
    handler.send_header = lambda k, v: captured.setdefault("headers", []).append((k, v))
    handler.end_headers = lambda: None

    handler.do_GET()

    assert captured["status"] == 200
    body = json.loads(handler.wfile.buf.decode("utf-8"))
    assert body["status"] == "ok"
    assert "sessions" in body
    assert isinstance(body["sessions"], list)


def test_healthz_lists_configured_sessions(fake_config, tmp_workdir):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)

    class FakeWFile:
        def __init__(self): self.buf = b""
        def write(self, b):  self.buf += b

    handler.path = "/healthz"
    handler.wfile = FakeWFile()
    handler.send_response = lambda code: None
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None

    handler.do_GET()

    body = json.loads(handler.wfile.buf.decode("utf-8"))
    assert "1" in body["sessions"]


def test_get_unknown_path_returns_404(fake_config):
    ws = _import_ws()
    handler = ws.WebhookHandler.__new__(ws.WebhookHandler)

    captured = {}
    class FakeWFile:
        def __init__(self): self.buf = b""
        def write(self, b):  self.buf += b

    handler.path = "/random"
    handler.wfile = FakeWFile()
    handler.send_response = lambda code: captured.setdefault("status", code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None

    handler.do_GET()
    assert captured["status"] == 404
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_healthz.py -v`
Expected: FAIL — `WebhookHandler` não tem `do_GET` (só `do_POST`).

- [ ] **Step 3: Add `do_GET` to `WebhookHandler` in `webhook_server.py`**

After the `do_POST` method (around line 47), add:

```python
    def do_GET(self):
        if self.path == "/healthz":
            from config import SESSIONS
            body = json.dumps({
                "status": "ok",
                "sessions": list(SESSIONS.keys()),
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
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_healthz.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run full suite to ensure no regression**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (anteriormente 26 + 3 novos = 29)

- [ ] **Step 6: Commit**

```bash
git add webhook_server.py tests/test_healthz.py
git commit -m "feat(webhook): GET /healthz endpoint para Cloudflare + monitoring"
```

---

## Task 2: systemd unit pro webhook_server.py

**Files:**
- Create: `systemd/webhook.service`
- Create: `tests/test_systemd_units.py`

- [ ] **Step 1: Write failing test** que valida sintaxe + campos obrigatórios

```python
"""Tests for systemd unit files."""
import os
import re


SYSTEMD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "systemd")


def _parse_unit(path):
    """Parse simple INI-like systemd unit. Returns dict of section -> dict of key -> value (str or list)."""
    sections = {}
    current = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
                sections[current] = {}
                continue
            if "=" in line and current:
                k, v = line.split("=", 1)
                k = k.strip(); v = v.strip()
                if k in sections[current]:
                    if isinstance(sections[current][k], list):
                        sections[current][k].append(v)
                    else:
                        sections[current][k] = [sections[current][k], v]
                else:
                    sections[current][k] = v
    return sections


def test_webhook_service_exists():
    assert os.path.exists(os.path.join(SYSTEMD_DIR, "webhook.service"))


def test_webhook_service_required_sections():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    assert "Unit" in u
    assert "Service" in u
    assert "Install" in u


def test_webhook_service_restart_policy():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    assert u["Service"].get("Restart") in ("on-failure", "always")
    assert "RestartSec" in u["Service"]


def test_webhook_service_runs_python_script():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    exec_start = u["Service"]["ExecStart"]
    assert "python" in exec_start.lower()
    assert "webhook_server.py" in exec_start


def test_webhook_service_uses_dedicated_user():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    assert u["Service"].get("User") == "whatsapp"


def test_webhook_service_logs_to_journal():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    assert u["Service"].get("StandardOutput") == "journal"
    assert u["Service"].get("StandardError") == "journal"


def test_webhook_service_enabled_for_multi_user():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "webhook.service"))
    assert u["Install"].get("WantedBy") == "multi-user.target"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: FAIL — diretório `systemd/` não existe.

- [ ] **Step 3: Create `systemd/webhook.service`**

```ini
[Unit]
Description=WhatsApp Claude Agent webhook server
Documentation=https://github.com/mbkautomacoes/zyon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=whatsapp
Group=whatsapp
WorkingDirectory=/opt/whatsapp-claude-agent
ExecStart=/usr/bin/python3 /opt/whatsapp-claude-agent/webhook_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add systemd/webhook.service tests/test_systemd_units.py
git commit -m "feat(systemd): unit pro webhook_server com hardening basico"
```

---

## Task 3: systemd unit pro cloudflared

**Files:**
- Create: `systemd/cloudflared.service`
- Modify: `tests/test_systemd_units.py` (add tests)

- [ ] **Step 1: Add failing tests**

Append ao final de `tests/test_systemd_units.py`:

```python
def test_cloudflared_service_exists():
    assert os.path.exists(os.path.join(SYSTEMD_DIR, "cloudflared.service"))


def test_cloudflared_service_runs_tunnel():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "cloudflared.service"))
    assert "tunnel" in u["Service"]["ExecStart"].lower()


def test_cloudflared_service_restart_always():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "cloudflared.service"))
    assert u["Service"].get("Restart") == "always"


def test_cloudflared_after_webhook():
    """Cloudflared deve subir DEPOIS que o webhook esta pronto."""
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "cloudflared.service"))
    after = u["Unit"].get("After", "")
    after_list = after if isinstance(after, list) else [after]
    flat = " ".join(after_list)
    assert "webhook.service" in flat or "network-online.target" in flat
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: FAIL — `cloudflared.service` não existe.

- [ ] **Step 3: Create `systemd/cloudflared.service`**

```ini
[Unit]
Description=Cloudflare Tunnel para WhatsApp Claude Agent
Documentation=https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
After=network-online.target webhook.service
Wants=network-online.target webhook.service

[Service]
Type=simple
User=whatsapp
Group=whatsapp
ExecStart=/usr/local/bin/cloudflared --no-autoupdate tunnel --config /etc/cloudflared/config.yml run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: PASS (11 tests total)

- [ ] **Step 5: Commit**

```bash
git add systemd/cloudflared.service tests/test_systemd_units.py
git commit -m "feat(systemd): unit pro cloudflared tunnel apontando webhook :3020"
```

---

## Task 4: systemd unit pro tmux com Claude Code

**Files:**
- Create: `systemd/whatsapp-tmux.service`
- Create: `install/start_claude_tmux.sh`
- Modify: `tests/test_systemd_units.py` (add tests)

- [ ] **Step 1: Add failing tests**

Append:

```python
def test_tmux_service_exists():
    assert os.path.exists(os.path.join(SYSTEMD_DIR, "whatsapp-tmux.service"))


def test_tmux_service_runs_start_script():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "whatsapp-tmux.service"))
    assert "start_claude_tmux.sh" in u["Service"]["ExecStart"]


def test_tmux_service_after_webhook():
    u = _parse_unit(os.path.join(SYSTEMD_DIR, "whatsapp-tmux.service"))
    after = u["Unit"].get("After", "")
    after_list = after if isinstance(after, list) else [after]
    flat = " ".join(after_list)
    assert "webhook.service" in flat


def test_start_claude_tmux_script_exists_and_executable():
    script = os.path.join(os.path.dirname(SYSTEMD_DIR), "install", "start_claude_tmux.sh")
    assert os.path.exists(script)
    # On Windows we cannot check execute bit, so just verify shebang
    with open(script, encoding="utf-8") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!/")


def test_start_claude_tmux_creates_session():
    script = os.path.join(os.path.dirname(SYSTEMD_DIR), "install", "start_claude_tmux.sh")
    with open(script, encoding="utf-8") as f:
        content = f.read()
    # Must create or attach to a tmux session named whatsapp-agent
    assert "tmux new-session" in content or "tmux new" in content
    assert "whatsapp-agent" in content
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: FAIL — script + unit não existem.

- [ ] **Step 3: Create `install/start_claude_tmux.sh`**

```bash
#!/usr/bin/env bash
# ============================================================
# start_claude_tmux.sh
# ----------------------------------------------------------
# Sobe sessao tmux 'whatsapp-agent' rodando 'claude' na pasta
# do projeto. Idempotente: se sessao ja existe, sai sem erro.
# Pra anexar manualmente: tmux attach -t whatsapp-agent
# Pra parar: tmux kill-session -t whatsapp-agent
# ============================================================
set -euo pipefail

SESSION="whatsapp-agent"
PROJECT_DIR="${PROJECT_DIR:-/opt/whatsapp-claude-agent}"
SESSION_NUM="${SESSION_NUM:-1}"

# Verifica se tmux esta instalado
if ! command -v tmux >/dev/null 2>&1; then
    echo "ERROR: tmux nao instalado. apt install tmux" >&2
    exit 1
fi

# Verifica se claude CLI esta instalado
if ! command -v claude >/dev/null 2>&1; then
    echo "ERROR: claude CLI nao instalado. Veja https://docs.anthropic.com/claude-code" >&2
    exit 1
fi

# Idempotencia: sai se sessao ja existe
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Sessao tmux '$SESSION' ja ativa. Pra anexar: tmux attach -t $SESSION"
    exit 0
fi

# Cria sessao detached, entra no projeto, roda claude
tmux new-session -d -s "$SESSION" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION" "claude" C-m

echo "Sessao tmux '$SESSION' iniciada com claude em $PROJECT_DIR"
echo "Anexar: tmux attach -t $SESSION"
echo ""
echo "PROXIMO PASSO MANUAL: anexe e cole o prompt do CLAUDE_PROMPT.md"
echo "(Trocar monitor.py 1 -> monitor.py $SESSION_NUM se precisar)"
```

- [ ] **Step 4: Make executable**

```bash
chmod +x install/start_claude_tmux.sh
```

- [ ] **Step 5: Create `systemd/whatsapp-tmux.service`**

```ini
[Unit]
Description=Sessao tmux com Claude Code agente WhatsApp
Documentation=file:///opt/whatsapp-claude-agent/docs/VPS_OPERATIONS.md
After=network-online.target webhook.service
Wants=webhook.service

[Service]
Type=forking
User=whatsapp
Group=whatsapp
WorkingDirectory=/opt/whatsapp-claude-agent
Environment="PROJECT_DIR=/opt/whatsapp-claude-agent"
Environment="SESSION_NUM=1"
ExecStart=/opt/whatsapp-claude-agent/install/start_claude_tmux.sh
ExecStop=/usr/bin/tmux kill-session -t whatsapp-agent
RemainAfterExit=yes
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 6: Run tests, verify PASS**

Run: `python -m pytest tests/test_systemd_units.py -v`
Expected: PASS (16 tests total)

- [ ] **Step 7: Bash syntax check**

```bash
bash -n install/start_claude_tmux.sh
```
Expected: no output (valid).

- [ ] **Step 8: Commit**

```bash
git add systemd/whatsapp-tmux.service install/start_claude_tmux.sh tests/test_systemd_units.py
git commit -m "feat(systemd): tmux unit pra rodar Claude Code 24/7 em VPS"
```

---

## Task 5: Cloudflare Tunnel setup script

**Files:**
- Create: `install/cloudflared_setup.sh`
- Create: `tests/test_cloudflared_setup.py`

- [ ] **Step 1: Write failing test** (smoke test do script: sintaxe + presença de comandos chave)

```python
"""Tests for cloudflared_setup.sh."""
import os
import subprocess


SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "install", "cloudflared_setup.sh",
)


def test_script_exists():
    assert os.path.exists(SCRIPT)


def test_script_has_shebang():
    with open(SCRIPT, encoding="utf-8") as f:
        first = f.readline().strip()
    assert first.startswith("#!/usr/bin/env bash") or first.startswith("#!/bin/bash")


def test_script_runs_in_strict_mode():
    with open(SCRIPT, encoding="utf-8") as f:
        content = f.read()
    assert "set -euo pipefail" in content


def test_script_calls_cloudflared_login():
    with open(SCRIPT, encoding="utf-8") as f:
        content = f.read()
    assert "cloudflared tunnel login" in content


def test_script_calls_cloudflared_create():
    with open(SCRIPT, encoding="utf-8") as f:
        content = f.read()
    assert "cloudflared tunnel create" in content


def test_script_writes_config_yml():
    with open(SCRIPT, encoding="utf-8") as f:
        content = f.read()
    assert "/etc/cloudflared/config.yml" in content


def test_script_routes_dns():
    with open(SCRIPT, encoding="utf-8") as f:
        content = f.read()
    assert "cloudflared tunnel route dns" in content


def test_script_bash_syntax_valid():
    """bash -n confirma sintaxe sem executar."""
    result = subprocess.run(
        ["bash", "-n", SCRIPT], capture_output=True, text=True
    )
    assert result.returncode == 0, f"Syntax error: {result.stderr}"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_cloudflared_setup.py -v`
Expected: FAIL — script não existe.

- [ ] **Step 3: Create `install/cloudflared_setup.sh`**

```bash
#!/usr/bin/env bash
# ============================================================
# cloudflared_setup.sh
# ----------------------------------------------------------
# Configura Cloudflare Tunnel para o webhook do agente.
#
# Pre-requisito:
#   - conta Cloudflare com 1 dominio adicionado
#   - cloudflared instalado (deploy_vps.sh cuida disso)
#
# Uso interativo:
#   sudo ./install/cloudflared_setup.sh agent.seu-dominio.com
# ============================================================
set -euo pipefail

HOSTNAME="${1:-}"
TUNNEL_NAME="${TUNNEL_NAME:-whatsapp-agent}"
LOCAL_SERVICE="${LOCAL_SERVICE:-http://localhost:3020}"
CONFIG_DIR="/etc/cloudflared"
CONFIG_FILE="${CONFIG_DIR}/config.yml"

if [ -z "$HOSTNAME" ]; then
    echo "Uso: sudo $0 <hostname-publico>"
    echo "Ex:  sudo $0 agent.exemplo.com"
    exit 1
fi

# 1. Login interativo (abre URL no browser/terminal)
echo "==> Passo 1: cloudflared tunnel login (abre URL pra autorizar dominio)"
cloudflared tunnel login

# 2. Criar tunnel se nao existir
EXISTING_ID=$(cloudflared tunnel list -o json 2>/dev/null \
    | python3 -c "import sys, json; tns=json.load(sys.stdin); print(next((t['id'] for t in tns if t['name']=='$TUNNEL_NAME'), ''))" \
    || true)

if [ -n "$EXISTING_ID" ]; then
    TUNNEL_ID="$EXISTING_ID"
    echo "==> Tunnel '$TUNNEL_NAME' ja existe (id $TUNNEL_ID), reaproveitando."
else
    echo "==> Passo 2: criando tunnel '$TUNNEL_NAME'"
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list -o json \
        | python3 -c "import sys, json; tns=json.load(sys.stdin); print(next(t['id'] for t in tns if t['name']=='$TUNNEL_NAME'))")
fi

# 3. Roteia DNS para o tunnel (subdominio -> tunnel)
echo "==> Passo 3: cloudflared tunnel route dns $TUNNEL_NAME $HOSTNAME"
cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME"

# 4. Escreve /etc/cloudflared/config.yml
mkdir -p "$CONFIG_DIR"
CRED_PATH="$HOME/.cloudflared/${TUNNEL_ID}.json"

cat > "$CONFIG_FILE" <<EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CRED_PATH}

ingress:
  - hostname: ${HOSTNAME}
    service: ${LOCAL_SERVICE}
  - service: http_status:404
EOF

# Copia credenciais pra path estavel + ajusta dono
cp "$CRED_PATH" "$CONFIG_DIR/${TUNNEL_ID}.json"
chown -R whatsapp:whatsapp "$CONFIG_DIR" 2>/dev/null || true
chmod 600 "$CONFIG_DIR/${TUNNEL_ID}.json"

# Atualiza config.yml pra usar credentials-file dentro de /etc/cloudflared
sed -i "s|credentials-file: .*|credentials-file: $CONFIG_DIR/${TUNNEL_ID}.json|" "$CONFIG_FILE"

echo ""
echo "==> Tunnel configurado!"
echo "    Tunnel ID:   $TUNNEL_ID"
echo "    Hostname:    https://${HOSTNAME}"
echo "    Webhook URL: https://${HOSTNAME}/?session=1"
echo ""
echo "Cole no painel megaAPI: https://${HOSTNAME}/?session=1"
echo ""
echo "Proximo: systemctl enable --now cloudflared"
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_cloudflared_setup.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
chmod +x install/cloudflared_setup.sh
git add install/cloudflared_setup.sh tests/test_cloudflared_setup.py
git commit -m "feat(install): cloudflared_setup.sh registra tunnel + DNS + config.yml"
```

---

## Task 6: deploy_vps.sh idempotente

**Files:**
- Create: `install/deploy_vps.sh`
- Create: `tests/test_deploy_vps.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for deploy_vps.sh."""
import os
import subprocess


SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "install", "deploy_vps.sh",
)


def _content():
    with open(SCRIPT, encoding="utf-8") as f:
        return f.read()


def test_script_exists():
    assert os.path.exists(SCRIPT)


def test_script_strict_mode():
    assert "set -euo pipefail" in _content()


def test_installs_python_curl_tmux():
    c = _content()
    assert "python3" in c
    assert "tmux" in c
    assert "curl" in c


def test_installs_cloudflared():
    c = _content()
    assert "cloudflared" in c
    # binary download or apt install
    assert ("github.com/cloudflare/cloudflared" in c) or ("apt install" in c and "cloudflared" in c)


def test_creates_system_user_whatsapp():
    c = _content()
    assert "useradd" in c or "adduser" in c
    assert "whatsapp" in c


def test_clones_repo_to_opt():
    c = _content()
    assert "/opt/whatsapp-claude-agent" in c


def test_installs_systemd_units():
    c = _content()
    assert "/etc/systemd/system/" in c
    assert "webhook.service" in c
    assert "cloudflared.service" in c
    assert "whatsapp-tmux.service" in c


def test_enables_systemd_units():
    c = _content()
    assert "systemctl enable" in c
    assert "systemctl daemon-reload" in c


def test_idempotent_repo_clone():
    """Se repo ja existe, faz git pull em vez de clone."""
    c = _content()
    assert "git pull" in c or "if [ -d" in c


def test_runs_setup_config():
    c = _content()
    assert "setup_config.py" in c


def test_bash_syntax_valid():
    result = subprocess.run(["bash", "-n", SCRIPT], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax: {result.stderr}"


def test_must_run_as_root():
    c = _content()
    assert "EUID" in c or "id -u" in c or "whoami" in c
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_deploy_vps.py -v`
Expected: FAIL — script não existe.

- [ ] **Step 3: Create `install/deploy_vps.sh`**

```bash
#!/usr/bin/env bash
# ============================================================
# deploy_vps.sh
# ----------------------------------------------------------
# Bootstrap idempotente do agente WhatsApp em VPS Ubuntu/Debian.
#
# Uso:
#   sudo bash install/deploy_vps.sh
#
# Pre-requisitos minimos:
#   - VPS Ubuntu 22.04 LTS ou Debian 12 (root SSH disponivel)
#   - Dominio Cloudflare em maos (configurado depois via cloudflared_setup.sh)
# ============================================================
set -euo pipefail

# --- config ---
REPO_URL="${REPO_URL:-https://github.com/mbkautomacoes/zyon.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/whatsapp-claude-agent}"
SYS_USER="${SYS_USER:-whatsapp}"

# --- guards ---
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: rode como root (sudo bash $0)" >&2
    exit 1
fi

echo "=========================================="
echo "WhatsApp Claude Agent - VPS Deploy (Trilha 2)"
echo "=========================================="
echo ""

# --- 1. Pacotes base ---
echo "==> [1/8] apt update + instalando dependencias"
apt-get update -y
apt-get install -y python3 python3-pip curl tmux git ca-certificates

# --- 2. cloudflared (binario oficial) ---
echo "==> [2/8] instalando cloudflared"
if ! command -v cloudflared >/dev/null 2>&1; then
    ARCH=$(dpkg --print-architecture)
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}" \
         -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    echo "    cloudflared $(cloudflared --version | head -1)"
else
    echo "    cloudflared ja instalado: $(cloudflared --version | head -1)"
fi

# --- 3. Usuario sistema dedicado ---
echo "==> [3/8] criando usuario sistema '$SYS_USER'"
if ! id -u "$SYS_USER" >/dev/null 2>&1; then
    useradd --system --create-home --shell /bin/bash "$SYS_USER"
    echo "    usuario '$SYS_USER' criado"
else
    echo "    usuario '$SYS_USER' ja existe"
fi

# --- 4. Clone / atualiza repo ---
echo "==> [4/8] preparando $INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "    repo ja clonado, fazendo git pull"
    su - "$SYS_USER" -c "cd $INSTALL_DIR && git pull origin $REPO_BRANCH"
else
    echo "    clonando $REPO_URL"
    git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
    chown -R "$SYS_USER:$SYS_USER" "$INSTALL_DIR"
fi

# --- 5. config.py via wizard interativo ---
echo "==> [5/8] config.py"
if [ ! -f "$INSTALL_DIR/config.py" ]; then
    echo "    Rodando setup_config.py (interativo)..."
    su - "$SYS_USER" -c "cd $INSTALL_DIR && python3 setup_config.py"
else
    echo "    config.py ja existe, pulando wizard"
fi

# --- 6. systemd units ---
echo "==> [6/8] instalando systemd units"
cp "$INSTALL_DIR/systemd/webhook.service"        /etc/systemd/system/webhook.service
cp "$INSTALL_DIR/systemd/cloudflared.service"    /etc/systemd/system/cloudflared.service
cp "$INSTALL_DIR/systemd/whatsapp-tmux.service"  /etc/systemd/system/whatsapp-tmux.service
systemctl daemon-reload

# --- 7. Enable + start webhook ---
echo "==> [7/8] enable + start webhook.service"
systemctl enable webhook.service
systemctl restart webhook.service
sleep 2
if systemctl is-active --quiet webhook; then
    echo "    webhook.service ativo (porta :3020)"
else
    echo "    AVISO: webhook.service nao ativo. Veja: journalctl -u webhook -n 30"
fi

# --- 8. Mensagem final ---
echo ""
echo "=========================================="
echo "Deploy base concluido."
echo "=========================================="
echo ""
echo "Proximos passos manuais:"
echo ""
echo "  1) Configurar Cloudflare Tunnel:"
echo "     sudo bash $INSTALL_DIR/install/cloudflared_setup.sh agent.seu-dominio.com"
echo ""
echo "  2) Habilitar cloudflared:"
echo "     sudo systemctl enable --now cloudflared"
echo ""
echo "  3) Login no Claude Code (1a vez, interativo):"
echo "     su - $SYS_USER"
echo "     claude   (faz login)"
echo "     exit"
echo ""
echo "  4) Habilitar tmux unit (Claude Code 24/7):"
echo "     sudo systemctl enable --now whatsapp-tmux"
echo "     sudo -u $SYS_USER tmux attach -t whatsapp-agent"
echo "     # cole o prompt do CLAUDE_PROMPT.md, depois Ctrl-b d pra desanexar"
echo ""
echo "  5) Ver status:"
echo "     systemctl status webhook cloudflared whatsapp-tmux"
echo "     journalctl -u webhook -u cloudflared -f"
echo ""
echo "Doc completa: $INSTALL_DIR/docs/VPS_OPERATIONS.md"
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_deploy_vps.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
chmod +x install/deploy_vps.sh
git add install/deploy_vps.sh tests/test_deploy_vps.py
git commit -m "feat(install): deploy_vps.sh idempotente Ubuntu/Debian"
```

---

## Task 7: Mover install.{ps1,sh} para install/ com shims na raiz

**Files:**
- Move: `install.ps1` -> `install/install.ps1`
- Move: `install.sh` -> `install/install.sh`
- Create: `install.ps1` (shim na raiz)
- Create: `install.sh` (shim na raiz)
- Create: `tests/test_install_layout.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for install/ layout + shims."""
import os
import subprocess


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_install_dir_exists():
    assert os.path.isdir(os.path.join(ROOT, "install"))


def test_install_sh_in_install_dir():
    assert os.path.exists(os.path.join(ROOT, "install", "install.sh"))


def test_install_ps1_in_install_dir():
    assert os.path.exists(os.path.join(ROOT, "install", "install.ps1"))


def test_root_shim_install_sh_calls_install_dir():
    """Root install.sh deve apenas redirecionar para install/install.sh."""
    path = os.path.join(ROOT, "install.sh")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "install/install.sh" in content


def test_root_shim_install_ps1_calls_install_dir():
    path = os.path.join(ROOT, "install.ps1")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "install\\install.ps1" in content or "install/install.ps1" in content


def test_install_dir_sh_syntax_valid():
    result = subprocess.run(
        ["bash", "-n", os.path.join(ROOT, "install", "install.sh")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_root_shim_sh_syntax_valid():
    result = subprocess.run(
        ["bash", "-n", os.path.join(ROOT, "install.sh")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_install_layout.py -v`
Expected: FAIL — `install/install.sh` não existe (ainda em raiz).

- [ ] **Step 3: Move scripts**

```bash
git mv install.sh install/install.sh
git mv install.ps1 install/install.ps1
```

- [ ] **Step 4: Create root shim `install.sh`**

```bash
#!/usr/bin/env bash
# Shim: install.sh foi movido para install/install.sh (Trilha 2 layout).
# Este shim mantem compat com README/docs antigos.
exec "$(dirname "$0")/install/install.sh" "$@"
```

- [ ] **Step 5: Create root shim `install.ps1`**

```powershell
# Shim: install.ps1 foi movido para install/install.ps1 (Trilha 2 layout).
# Este shim mantem compat com README/docs antigos.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$ScriptDir\install\install.ps1" @args
exit $LASTEXITCODE
```

- [ ] **Step 6: Make root shims executable**

```bash
chmod +x install.sh
```

- [ ] **Step 7: Run tests, verify PASS**

Run: `python -m pytest tests/test_install_layout.py -v`
Expected: PASS (7 tests)

- [ ] **Step 8: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (29 + novos da Trilha 2 = ~52)

- [ ] **Step 9: Commit**

```bash
git add install/ install.sh install.ps1 tests/test_install_layout.py
git commit -m "refactor(install): mover install.{ps1,sh} pra install/ com shims na raiz"
```

---

## Task 8: doctor.py modo VPS

**Files:**
- Modify: `doctor.py`
- Create: `tests/test_doctor_vps.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for doctor.py VPS mode checks."""
import os
import sys
from unittest.mock import patch, MagicMock


def _import():
    sys.modules.pop("doctor", None)
    import doctor
    return doctor


def test_check_vps_mode_skips_when_no_systemd(fake_config, capsys):
    d = _import()
    with patch("doctor.shutil.which", return_value=None):
        d.check_vps_mode()
    out = capsys.readouterr().out
    assert "VPS mode" in out
    assert "systemctl nao encontrado" in out


def test_check_vps_mode_reports_active_units(fake_config, capsys):
    d = _import()

    def fake_run(args, **kw):
        # Simulate systemctl is-active for each unit
        if "is-active" in args:
            return MagicMock(stdout="active\n", returncode=0)
        return MagicMock(stdout="", returncode=0)

    with patch("doctor.shutil.which", return_value="/usr/bin/systemctl"), \
         patch("doctor.subprocess.run", side_effect=fake_run):
        d.check_vps_mode()
    out = capsys.readouterr().out
    assert "webhook.service: active" in out
    assert "cloudflared.service: active" in out
    assert "whatsapp-tmux.service: active" in out


def test_check_vps_mode_flags_inactive_units(fake_config, capsys):
    d = _import()

    def fake_run(args, **kw):
        if "is-active" in args and "webhook" in args[-1]:
            return MagicMock(stdout="inactive\n", returncode=3)
        return MagicMock(stdout="active\n", returncode=0)

    with patch("doctor.shutil.which", return_value="/usr/bin/systemctl"), \
         patch("doctor.subprocess.run", side_effect=fake_run):
        d.check_vps_mode()
    out = capsys.readouterr().out
    assert "[ERRO]" in out and "webhook.service" in out
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_doctor_vps.py -v`
Expected: FAIL — `check_vps_mode` não existe.

- [ ] **Step 3: Add `check_vps_mode` to `doctor.py`**

Antes de `def main()`, adicione:

```python
def check_vps_mode():
    """Checa unidades systemd quando rodando em VPS. No-op em Windows."""
    if not shutil.which("systemctl"):
        warn("VPS mode: systemctl nao encontrado (provavelmente localhost dev)")
        return

    units = ("webhook.service", "cloudflared.service", "whatsapp-tmux.service")
    for unit in units:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True, text=True, timeout=5,
            )
            state = result.stdout.strip()
            if state == "active":
                ok(f"{unit}: active")
            elif state == "inactive":
                err(f"{unit}: inactive (rode: sudo systemctl start {unit})")
            elif state == "failed":
                err(f"{unit}: failed (veja: journalctl -u {unit} -n 30)")
            else:
                warn(f"{unit}: {state}")
        except Exception as e:
            warn(f"{unit}: erro ao consultar systemctl ({e})")
```

E em `main()`, depois da seção `[MULTIMODAL]` e antes de `[FILES]`:

```python
    print("")
    print("[VPS]")
    check_vps_mode()
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_doctor_vps.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add doctor.py tests/test_doctor_vps.py
git commit -m "feat(doctor): check_vps_mode valida systemd units (webhook, cloudflared, tmux)"
```

---

## Task 9: CLAUDE_PROMPT.md seção Modo VPS

**Files:**
- Modify: `CLAUDE_PROMPT.md`

- [ ] **Step 1: Adicionar seção** após o bloco "## Pre-requisito — webhook + ngrok rodando (FORA do Claude Code)" — substituir a seção "Opcao C — VPS producao (24/7)" pelo conteúdo expandido abaixo.

Localize na seção "Opcao C" e SUBSTITUA por:

```markdown
### Opcao C — VPS producao (24/7) — **Trilha 2**

Para deploy em VPS Linux 24/7 com Cloudflare Tunnel + systemd + tmux:

**Requisitos:** VPS Ubuntu 22.04 / Debian 12, conta Cloudflare com 1 dominio,
acesso root SSH.

**Passos:**

```bash
# 1. SSH no VPS como root
ssh root@SEU-VPS-IP

# 2. Bootstrap (clona repo, instala deps, cria units, sobe webhook)
curl -fsSL https://raw.githubusercontent.com/mbkautomacoes/zyon/main/install/deploy_vps.sh | sudo bash
# OU (apos clone manual):
sudo bash /opt/whatsapp-claude-agent/install/deploy_vps.sh

# 3. Cloudflare Tunnel (registra dominio publico)
sudo bash /opt/whatsapp-claude-agent/install/cloudflared_setup.sh agent.SEU-DOMINIO.com
sudo systemctl enable --now cloudflared

# 4. Login Claude Code (1x, interativo)
su - whatsapp
claude    # faz login Anthropic
exit

# 5. Ativa sessao tmux com Claude Code 24/7
sudo systemctl enable --now whatsapp-tmux
sudo -u whatsapp tmux attach -t whatsapp-agent
# Cole o PROMPT inteiro abaixo, depois Ctrl-b d pra desanexar (Claude continua rodando)

# 6. Verifica saude completa
sudo -u whatsapp /opt/whatsapp-claude-agent/doctor.py
```

**Webhook URL para colar no painel megaAPI:**
```
https://agent.SEU-DOMINIO.com/?session=1
```

**Operacao do dia-a-dia:**
- Ver logs: `journalctl -u webhook -u cloudflared -u whatsapp-tmux -f`
- Restart webhook: `sudo systemctl restart webhook`
- Anexar Claude Code: `sudo -u whatsapp tmux attach -t whatsapp-agent`
- Desanexar (Claude segue rodando): `Ctrl-b d`
- Healthcheck externo: `curl https://agent.SEU-DOMINIO.com/healthz`

Doc completa: `docs/VPS_OPERATIONS.md`.
```

- [ ] **Step 2: Verificar markdown render**

Abra `CLAUDE_PROMPT.md` em qualquer renderer markdown e confirme que as seções A/B/C aparecem completas e a nova C tem comandos numerados.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE_PROMPT.md
git commit -m "docs(prompt): expandir Opcao C com fluxo VPS completo (Trilha 2)"
```

---

## Task 10: docs/VPS_OPERATIONS.md runbook

**Files:**
- Create: `docs/VPS_OPERATIONS.md`

- [ ] **Step 1: Write failing test** que valida presença + seções

```python
"""Tests for docs/VPS_OPERATIONS.md."""
import os


DOC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "VPS_OPERATIONS.md",
)


def test_doc_exists():
    assert os.path.exists(DOC)


def test_doc_has_required_sections():
    with open(DOC, encoding="utf-8") as f:
        content = f.read()
    required = [
        "## Deploy inicial",
        "## Operacao diaria",
        "## Logs",
        "## Restart",
        "## Backup",
        "## Troubleshooting",
        "## Update",
        "## Rollback",
    ]
    for s in required:
        assert s in content, f"Faltando: {s}"


def test_doc_references_systemctl_commands():
    with open(DOC, encoding="utf-8") as f:
        content = f.read()
    assert "systemctl restart webhook" in content
    assert "journalctl" in content


def test_doc_mentions_healthz():
    with open(DOC, encoding="utf-8") as f:
        content = f.read()
    assert "/healthz" in content
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest tests/test_vps_operations_doc.py -v`
Expected: FAIL — doc não existe.

(Salve o test acima como `tests/test_vps_operations_doc.py`.)

- [ ] **Step 3: Create `docs/VPS_OPERATIONS.md`**

```markdown
# VPS Operations Runbook

Operacao do dia-a-dia do agente WhatsApp Claude Agent rodando 24/7 em VPS
Linux (Ubuntu 22.04 / Debian 12) com Cloudflare Tunnel + systemd + tmux.

> Pre-requisito: deploy concluido via `install/deploy_vps.sh` + `install/cloudflared_setup.sh`.

---

## Deploy inicial

Veja `CLAUDE_PROMPT.md` secao "Opcao C" pro fluxo completo passo-a-passo.

Resumo:
1. `sudo bash install/deploy_vps.sh`
2. `sudo bash install/cloudflared_setup.sh agent.dominio.com`
3. `sudo systemctl enable --now cloudflared`
4. `su - whatsapp && claude` (login 1x) `exit`
5. `sudo systemctl enable --now whatsapp-tmux`
6. `sudo -u whatsapp tmux attach -t whatsapp-agent` (cola prompt, Ctrl-b d)

---

## Operacao diaria

| Ação | Comando |
|------|---------|
| Status geral | `systemctl status webhook cloudflared whatsapp-tmux` |
| Healthcheck externo | `curl https://agent.dominio.com/healthz` |
| Healthcheck completo | `sudo -u whatsapp /opt/whatsapp-claude-agent/doctor.py` |
| Anexar Claude Code | `sudo -u whatsapp tmux attach -t whatsapp-agent` |
| Desanexar (sem matar) | `Ctrl-b d` (dentro do tmux) |
| Listar sessoes tmux | `sudo -u whatsapp tmux list-sessions` |

---

## Logs

```bash
# Tail unificado de tudo
journalctl -u webhook -u cloudflared -u whatsapp-tmux -f

# Logs do webhook nas ultimas 100 linhas
journalctl -u webhook -n 100

# Logs do cloudflared nas ultimas 24h
journalctl -u cloudflared --since "24 hours ago"

# Filtrar por mensagem de erro
journalctl -u webhook -p err
```

Logs do Claude Code em si (dentro do tmux) **nao** vao pro journalctl
porque rodam em sessao tmux. Pra ver: anexe ao tmux.

---

## Restart

```bash
# Webhook (interrompe receber mensagens por ~2s)
sudo systemctl restart webhook

# Cloudflared (URL publica fica fora ~5s)
sudo systemctl restart cloudflared

# Tmux + Claude Code (mata sessao e recria)
sudo systemctl restart whatsapp-tmux
# Apos restart, anexe e cole o prompt novamente:
sudo -u whatsapp tmux attach -t whatsapp-agent
```

Reboot do VPS inteiro: tudo sobe sozinho via systemd. Apos reboot,
anexe ao tmux e re-cole o prompt do Claude Code.

---

## Backup

Itens criticos para backup periodico:

| Caminho | Conteudo | Frequencia |
|---------|----------|------------|
| `/opt/whatsapp-claude-agent/config.py` | Tokens megaAPI + OpenAI key | Toda vez que muda |
| `/etc/cloudflared/` | Tunnel ID + credenciais CF | 1x apos setup inicial |
| `/opt/whatsapp-claude-agent/messages_session*.jsonl` | Historico de msgs | Diario |
| `/opt/whatsapp-claude-agent/processed_ids_session*.txt` | IDs ja processados | Diario |

Script simples:

```bash
sudo tar czf /backup/whatsapp-$(date +%Y%m%d).tar.gz \
    /opt/whatsapp-claude-agent/config.py \
    /opt/whatsapp-claude-agent/messages_session*.jsonl \
    /opt/whatsapp-claude-agent/processed_ids_session*.txt \
    /etc/cloudflared/
```

Cron diario (`crontab -e` como root):

```
0 3 * * * tar czf /backup/whatsapp-$(date +\%Y\%m\%d).tar.gz /opt/whatsapp-claude-agent/config.py /opt/whatsapp-claude-agent/messages_session*.jsonl /etc/cloudflared/
```

---

## Update

Pra puxar nova versao do repo (Trilha 1 patches, etc):

```bash
sudo systemctl stop whatsapp-tmux webhook cloudflared
sudo -u whatsapp git -C /opt/whatsapp-claude-agent pull origin main

# Se o pull trouxer mudancas em systemd/, reinstale:
sudo cp /opt/whatsapp-claude-agent/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl start webhook cloudflared whatsapp-tmux
```

Verifique apos: `sudo -u whatsapp /opt/whatsapp-claude-agent/doctor.py`

---

## Rollback

Se update quebrou algo:

```bash
sudo systemctl stop whatsapp-tmux webhook cloudflared

# Voltar pro tag estavel
sudo -u whatsapp git -C /opt/whatsapp-claude-agent checkout v1.0-trilha1
# ou tag anterior conhecida

sudo systemctl start webhook cloudflared whatsapp-tmux
```

---

## Troubleshooting

### Webhook nao responde

```bash
# 1. Esta rodando?
systemctl status webhook
# Se nao: sudo systemctl start webhook

# 2. Porta 3020 acessivel localmente?
curl http://127.0.0.1:3020/healthz
# Se 200 -> webhook OK

# 3. Cloudflared esta encaminhando?
systemctl status cloudflared
# Se inactive: sudo systemctl start cloudflared

# 4. URL publica responde?
curl https://agent.dominio.com/healthz
# Se 502/504 -> tunnel nao esta conectando ao webhook
# Veja: journalctl -u cloudflared -n 30
```

### Mensagens chegam mas Claude nao responde

```bash
# 1. Sessao tmux ativa?
sudo -u whatsapp tmux list-sessions
# Se nao tem 'whatsapp-agent': sudo systemctl restart whatsapp-tmux

# 2. Anexe e veja se Claude esta esperando o prompt:
sudo -u whatsapp tmux attach -t whatsapp-agent
# Se vazio ou na tela inicial: cole o prompt do CLAUDE_PROMPT.md

# 3. Monitor esta rodando dentro do Claude Code?
# (visivel na tela do Claude — deve haver indicador de Monitor ativo)
```

### Cloudflared 502/504 intermitente

```bash
# Restart cloudflared, geralmente resolve glitches de rede
sudo systemctl restart cloudflared

# Se persistir, recriar tunnel:
sudo cloudflared tunnel delete whatsapp-agent
sudo bash /opt/whatsapp-claude-agent/install/cloudflared_setup.sh agent.dominio.com
sudo systemctl restart cloudflared
```

### config.py corrompido / quero reconfigurar

```bash
sudo -u whatsapp mv /opt/whatsapp-claude-agent/config.py /opt/whatsapp-claude-agent/config.py.bak
sudo -u whatsapp python3 /opt/whatsapp-claude-agent/setup_config.py
sudo systemctl restart webhook
```

### Whisper nao transcreve / OPENAI_API_KEY mudou

```bash
sudo -u whatsapp $EDITOR /opt/whatsapp-claude-agent/config.py
# Edite OPENAI_API_KEY = "sk-..."
# transcribe.py le config a cada chamada — sem restart necessario
```

---

## Refs

- Trilha 2 plan: `docs/plans/2026-04-28-trilha-2-vps-deploy.md`
- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- systemd unit reference: `man systemd.service`
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `python -m pytest tests/test_vps_operations_doc.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add docs/VPS_OPERATIONS.md tests/test_vps_operations_doc.py
git commit -m "docs(vps): runbook completo (deploy, logs, restart, backup, troubleshoot)"
```

---

## Task 11: .gitignore secrets do Cloudflare

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add Cloudflare secret patterns** ao final de `.gitignore`

```
# Cloudflare Tunnel credentials (NUNCA commitar)
cloudflared-config.yml
*.pem
tunnel-*.json
.cloudflared/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): bloquear credenciais Cloudflare Tunnel"
```

---

## Task 12: Validacao em container Docker (sanity dry-run)

**Files:**
- Create: `install/Dockerfile.test` (Ubuntu 22.04 limpo, simulando VPS)
- Create: `tests/test_deploy_dryrun.py` (opcional, requer Docker)

- [ ] **Step 1: Create `install/Dockerfile.test`**

```dockerfile
# Dockerfile.test — Ubuntu 22.04 limpo pra validar deploy_vps.sh
# Build:  docker build -f install/Dockerfile.test -t whatsapp-deploy-test .
# Run:    docker run --rm -it whatsapp-deploy-test bash
#   (la dentro: bash /tmp/install/deploy_vps.sh)

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    sudo systemd systemd-sysv git \
    && rm -rf /var/lib/apt/lists/*

COPY install/ /tmp/install/
COPY systemd/ /tmp/install/systemd/
COPY *.py *.md requirements.txt /tmp/install/project/

WORKDIR /tmp/install
CMD ["bash"]
```

- [ ] **Step 2: Build + verify image**

```bash
docker build -f install/Dockerfile.test -t whatsapp-deploy-test .
```

Expected: build sucesso. (Skip se Docker indisponivel localmente.)

- [ ] **Step 3: Document manual validation steps** em `docs/VPS_OPERATIONS.md` (append):

```markdown
## Validacao local (sem VPS de verdade)

Pra validar o deploy script sem provisionar VPS real, use Docker:

```bash
docker build -f install/Dockerfile.test -t whatsapp-deploy-test .
docker run --rm -it whatsapp-deploy-test bash

# Dentro do container (privileged necessario pra systemd real):
docker run --privileged --rm -it whatsapp-deploy-test \
    bash -c "/lib/systemd/systemd & sleep 2 && bash /tmp/install/deploy_vps.sh"
```

Limitacoes do dry-run em container:
- Cloudflare Tunnel NAO pode ser registrado (precisa dominio real)
- Claude Code NAO pode ser logado (precisa browser/auth interativa)
- tmux unit NAO sobe sem login funcional do Claude Code

Validacao real: deploy num VPS de teste descartavel (DigitalOcean droplet
$6/mes ou similar).
```

- [ ] **Step 4: Commit**

```bash
git add install/Dockerfile.test docs/VPS_OPERATIONS.md
git commit -m "chore(test): Dockerfile pra dry-run de deploy_vps em Ubuntu 22.04"
```

---

## Task 13: Final sweep + tag v2.0-trilha2

**Files:** none (validation only)

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: ALL PASS (esperado: 26 da Trilha 1 + ~30 novos da Trilha 2 = ~56)

- [ ] **Step 2: Compile-check todos os Python files**

```bash
python -m py_compile webhook_server.py monitor.py send_message.py \
    config.example.py setup_config.py discover_lid.py \
    doctor.py add_session.py media_handler.py transcribe.py
```
Expected: no output.

- [ ] **Step 3: Bash syntax check de todos os scripts shell novos**

```bash
bash -n install/deploy_vps.sh
bash -n install/cloudflared_setup.sh
bash -n install/start_claude_tmux.sh
bash -n install.sh
```
Expected: no output (tudo valido).

- [ ] **Step 4: Update README.md** marcando Trilha 2 como concluída

Localize em README.md a seção "## Status" (ou "## Trilha 2 — VPS produção") e atualize:

```markdown
## Status

- Branch: `main`
- Trilha 1 (multi-sessao + multimodal) **concluida e validada E2E** em 2026-04-28
- Trilha 2 (VPS deploy 24/7) **concluida** em 2026-XX-XX (atualize com data real)
- ~56 testes pytest passando

## Trilha 2 — VPS produção (concluida)

Deploy 24/7 em VPS com Cloudflare Tunnel + systemd + tmux.
Ver [`docs/VPS_OPERATIONS.md`](./docs/VPS_OPERATIONS.md) para runbook completo.
Bootstrap: `sudo bash install/deploy_vps.sh`.
```

- [ ] **Step 5: Update PROJETO.md** roadmap section marcando Trilha 2 done

Substitua o item da Trilha 2 no roadmap com:

```markdown
| Trilha 2 | VPS deploy 24/7 | ✅ DONE 2026-XX-XX | tag v2.0-trilha2 |
```

- [ ] **Step 6: Final commit**

```bash
git add README.md PROJETO.md
git commit -m "docs: marcar Trilha 2 como concluida"
```

- [ ] **Step 7: Tag release**

```bash
git tag -a v2.0-trilha2 -m "Trilha 2: VPS deploy 24/7 (Cloudflare Tunnel + systemd + tmux)"
```

- [ ] **Step 8: Push to remote**

```bash
git push origin main
git push origin v2.0-trilha2
```

---

## Done Criteria

- [ ] ~30 novos unit tests pass (healthz + systemd units + scripts)
- [ ] `bash -n` valida todos os 4 shell scripts
- [ ] `python doctor.py` em VPS reporta todos os checks `[OK]`
- [ ] `curl https://agent.dominio.com/healthz` retorna `{"status":"ok",...}`
- [ ] WhatsApp -> agente em VPS responde texto/imagem/audio em <10s
- [ ] Reboot do VPS: webhook + cloudflared sobem automaticamente; tmux precisa apenas de re-cole do prompt manualmente
- [ ] Tag `v2.0-trilha2` criada e pushada
- [ ] `docs/VPS_OPERATIONS.md` cobre deploy, logs, restart, backup, update, rollback, troubleshooting
