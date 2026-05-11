"""
Adiciona uma nova sessao (usuario da API) ao config.py existente.

Usage: python -m whatsapp_agent.add_session

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


def append_session(token: str, phone: str) -> str:
    """Mutates config.py in-place. Returns new session id."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        content = f.read()

    ns: dict = {}
    exec(content, ns)
    sessions = ns.get("SESSIONS", {})
    new_id = next_session_id(sessions.keys())

    new_block = (
        f'    "{new_id}": {{\n'
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
    token = ask("Token da API")
    phone = normalize_phone(ask("Numero WhatsApp (5511999999999)"))
    if not phone:
        print("  ERRO: numero invalido.")
        return 1

    try:
        new_id = append_session(token, phone)
    except Exception as e:
        print(f"  ERRO: {e}")
        return 1

    print("")
    print(f"  OK: sessao '{new_id}' adicionada ao config.py")
    print("")
    print("Proximos passos:")
    print(f"  1. Configure webhook na API:")
    print(f"     python -m whatsapp_agent.update_webhooks")
    print(f"  2. Mande 1 mensagem WhatsApp pra voce mesmo")
    print(f"  3. Rode:  python -m whatsapp_agent.discover_lid {new_id}")
    print(f"  4. Em outra sessao Claude Code:  python -m whatsapp_agent.monitor {new_id}")
    print("")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Cancelado.")
        sys.exit(130)
