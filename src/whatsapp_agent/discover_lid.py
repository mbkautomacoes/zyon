"""
Auto-discover LID from incoming WhatsApp message.

Watches raw_debug.jsonl for the first message matching the configured phone,
extracts the LID, and updates config.py automatically.

Usage:
    python -m whatsapp_agent.discover_lid [session]   (default session: 1)

Steps for the user:
    1. Make sure webhook_server.py + cloudflared are running (./start.ps1 or .sh)
    2. Run this script
    3. Send any WhatsApp message to yourself
    4. Script auto-fills lid in config.py and exits
"""
import json
import os
import re
import sys
import time

from config import SESSIONS

RAW_FILE = "raw_debug.jsonl"
CONFIG_PATH = "config.py"


def find_lid_for_phone(phone: str, since_byte: int) -> tuple[str, int]:
    """Returns (lid, new_byte_pos). lid='' if not found yet."""
    if not os.path.exists(RAW_FILE):
        return "", since_byte
    with open(RAW_FILE, encoding="utf-8") as f:
        f.seek(since_byte)
        for line in f:
            try:
                data = json.loads(line)
            except Exception:
                continue

            # WuzAPI format: {"event": "Message", "instance": "...", "data": {...}}
            if data.get("event") != "Message":
                continue

            inner = data.get("data", {}) or {}
            jid = inner.get("chat", "") or inner.get("sender", "")

            if not jid:
                continue

            # match @lid format
            m = re.match(r"^(\d+)@lid$", jid)
            if m:
                return m.group(1), f.tell()
            # match @s.whatsapp.net with matching phone
            m2 = re.match(r"^(\d+)@s\.whatsapp\.net$", jid)
            if m2 and m2.group(1) == phone:
                return "", f.tell()  # phone ja esta no formato s.whatsapp.net, sem lid
        return "", f.tell()


def update_config_lid(session: str, new_lid: str) -> bool:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        content = f.read()

    # find the SESSIONS block for the given session and update lid
    pattern = re.compile(
        r'("' + re.escape(session) + r'"\s*:\s*\{[^}]*?"lid"\s*:\s*)"[^"]*"',
        re.DOTALL,
    )
    new_content, n = pattern.subn(r'\1"' + new_lid + '"', content, count=1)
    if n == 0:
        print(f"  AVISO: nao consegui localizar bloco da sessao '{session}' em {CONFIG_PATH}")
        print(f"  Edite manualmente: lid = '{new_lid}'")
        return False
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main() -> int:
    session = sys.argv[1] if len(sys.argv) > 1 else "1"

    if session not in SESSIONS:
        print(f"  ERRO: sessao '{session}' nao existe em config.SESSIONS")
        return 1

    phone = SESSIONS[session]["phone"]
    print("")
    print("=" * 60)
    print(f"Discover LID - sessao {session} - telefone {phone}")
    print("=" * 60)
    print("")
    print("  Aguardando mensagem WhatsApp...")
    print("  -> Mande agora qualquer mensagem do seu celular pra voce mesmo.")
    print("  (Ctrl+C para cancelar)")
    print("")

    # start at end of current file (only consider new messages)
    start_pos = os.path.getsize(RAW_FILE) if os.path.exists(RAW_FILE) else 0
    pos = start_pos
    timeout_s = 120
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        lid, pos = find_lid_for_phone(phone, pos)
        if lid:
            print(f"  OK: LID descoberto = {lid}")
            if update_config_lid(session, lid):
                print(f"  OK: config.py atualizado (sessao {session}, lid={lid})")
                print("")
                print("Reinicie o webhook para carregar nova config:")
                print("  Windows:  .\\stop.ps1; .\\start.ps1")
                print("  Linux:    ./stop.sh && ./start.sh")
                print("")
                return 0
            return 1
        time.sleep(1)

    print(f"  TIMEOUT ({timeout_s}s) sem mensagem. Verifique:")
    print("  - webhook_server.py esta rodando? (python -m whatsapp_agent.doctor)")
    print("  - URL do webhook configurada na API?")
    print("  - sua sessao WhatsApp esta conectada?")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Cancelado.")
        sys.exit(130)
