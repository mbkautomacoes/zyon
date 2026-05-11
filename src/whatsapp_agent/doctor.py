"""
Diagnostico do agente WhatsApp.

Roda checks rapidos e diz exatamente o que esta quebrado.

Usage: python -m whatsapp_agent.doctor
"""
import json
import os
import shutil
import socket
import subprocess
import sys
from urllib.request import urlopen


def ok(msg): print(f"  [OK]   {msg}")
def warn(msg): print(f"  [WARN] {msg}")
def err(msg): print(f"  [ERRO] {msg}")


def check_python():
    v = sys.version_info
    if v >= (3, 8):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    err(f"Python {v.major}.{v.minor} muito antigo. Precisa 3.8+")
    return False


def check_curl():
    if shutil.which("curl"):
        ok("curl disponivel")
        return True
    err("curl nao encontrado no PATH")
    return False


def check_cloudflared():
    if shutil.which("cloudflared"):
        ok("cloudflared disponivel")
        return True
    warn("cloudflared nao encontrado no PATH (winget install Cloudflare.cloudflared)")
    return False


def check_config():
    if not os.path.exists("config.py"):
        err("config.py nao existe. Rode: python -m whatsapp_agent.setup_config")
        return False, None
    try:
        from config import SESSIONS, CMD_TOKEN, API_HOST
    except Exception as e:
        err(f"config.py nao importa: {e}")
        return False, None

    if not SESSIONS:
        err("SESSIONS vazio em config.py")
        return False, None

    issues = 0
    for sid, cfg in SESSIONS.items():
        for key in ("token", "phone"):
            v = cfg.get(key, "")
            if not v or "CHANGE_ME" in str(v) or "SUA_" in str(v) or "SEU_" in str(v):
                err(f"sessao {sid}: campo '{key}' nao preenchido ({v!r})")
                issues += 1
        if not cfg.get("lid"):
            warn(f"sessao {sid}: lid vazio. Rode: python -m whatsapp_agent.discover_lid {sid}")

    if issues == 0:
        ok(f"config.py valido ({len(SESSIONS)} sessao(oes))")
    return issues == 0, SESSIONS


def check_webhook_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", 3020))
        ok("webhook_server.py rodando em :3020")
        return True
    except Exception:
        err("nada rodando em :3020. Rode: ./start.sh ou .\\start.ps1")
        return False
    finally:
        s.close()


def check_public_tunnel():
    try:
        from config import PUBLIC_WEBHOOK_URL
    except Exception:
        err("config.PUBLIC_WEBHOOK_URL ausente")
        return None
    if not PUBLIC_WEBHOOK_URL:
        err("config.PUBLIC_WEBHOOK_URL vazio")
        return None
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
             "-X", "POST", "-H", "Content-Type: application/json",
             "-d", "{}", PUBLIC_WEBHOOK_URL + "/?session=1"],
            capture_output=True, text=True, timeout=10,
        )
        code = result.stdout.strip()
        if code == "200":
            ok(f"tunnel publico OK: {PUBLIC_WEBHOOK_URL} (HTTP 200)")
            return PUBLIC_WEBHOOK_URL
        warn(f"tunnel respondeu HTTP {code} para {PUBLIC_WEBHOOK_URL}")
        return None
    except Exception as e:
        err(f"tunnel inalcancavel ({PUBLIC_WEBHOOK_URL}): {e}")
        return None


def check_api(sessions):
    if not sessions:
        return
    if not shutil.which("curl"):
        return
    try:
        from config import API_HOST
    except Exception:
        return
    for sid, cfg in sessions.items():
        if not cfg.get("token") or "CHANGE" in str(cfg.get("token", "")):
            continue
        full = f"{API_HOST}/session/status"
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", os.devnull, "-w", "%{http_code}",
                 "-H", f"token: {cfg['token']}",
                 full],
                capture_output=True, text=True, timeout=10
            )
            code = result.stdout.strip()
            if code in ("200", "201"):
                ok(f"API sessao {sid}: token valido ({code})")
            elif code == "401" or code == "403":
                err(f"API sessao {sid}: token invalido ({code})")
            elif code == "404":
                err(f"API sessao {sid}: endpoint nao encontrado ({code})")
            else:
                warn(f"API sessao {sid}: HTTP {code}")
        except Exception as e:
            warn(f"API sessao {sid}: erro de rede ({e})")


def check_runtime_files():
    files = [
        ("messages_session1.jsonl", "criado pelo webhook quando 1a msg chega"),
        ("raw_debug.jsonl",         "criado pelo webhook em qualquer requisicao"),
    ]
    for f, hint in files:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            ok(f"{f} tem dados")
        else:
            warn(f"{f} vazio - {hint}")


def check_openai():
    try:
        from config import OPENAI_API_KEY
    except ImportError:
        warn("config.py sem OPENAI_API_KEY (multimodal off)")
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


def main():
    print("")
    print("=" * 60)
    print("WhatsApp Claude Agent - Doctor")
    print("=" * 60)
    print("")
    print("[ENV]")
    check_python()
    check_curl()
    check_cloudflared()
    print("")
    print("[CONFIG]")
    config_ok, sessions = check_config()
    print("")
    print("[RUNTIME]")
    check_webhook_port()
    check_public_tunnel()
    print("")
    print("[API]")
    check_api(sessions)
    print("")
    print("[MULTIMODAL]")
    check_openai()
    print("")
    print("[FILES]")
    check_runtime_files()
    print("")
    print("Doctor done.")


if __name__ == "__main__":
    main()
