"""
Atualiza webhook URL em todas as sessoes da API a partir de config.PUBLIC_WEBHOOK_URL.

Uso: python -m whatsapp_agent.update_webhooks

Apos alterar PUBLIC_WEBHOOK_URL em config.py, rode este script para empurrar
a nova URL para cada usuario registrado em SESSIONS.
"""
import json
import subprocess
import sys

from config import PUBLIC_WEBHOOK_URL, API_HOST, SESSIONS


def configure(session_id: str, token: str) -> bool:
    url = f"{PUBLIC_WEBHOOK_URL}/?session={session_id}"
    body = json.dumps({
        "webhook": url,
        "events": ["Message"],
    })
    endpoint = f"{API_HOST}/webhook"
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", endpoint,
                "-H", f"token: {token}",
                "-H", "Content-Type: application/json",
                "-d", body,
            ],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        print(f"  [ERRO] sessao {session_id}: timeout (>15s) em {endpoint}")
        return False
    except OSError as e:
        print(f"  [ERRO] sessao {session_id}: falha ao executar curl ({e})")
        return False
    out = result.stdout.strip()
    try:
        data = json.loads(out)
    except Exception:
        print(f"  [ERRO] sessao {session_id}: resposta nao-JSON: {out!r}")
        return False
    if data.get("success") is True:
        print(f"  [OK]   sessao {session_id} -> {url}")
        return True
    print(f"  [ERRO] sessao {session_id}: {data}")
    return False


def main():
    if not PUBLIC_WEBHOOK_URL:
        print("ERRO: config.PUBLIC_WEBHOOK_URL vazio.")
        sys.exit(1)
    print(f"Atualizando webhooks para base: {PUBLIC_WEBHOOK_URL}")
    print("")
    failures = 0
    for sid, cfg in SESSIONS.items():
        if not cfg.get("token"):
            print(f"  [SKIP] sessao {sid}: token vazio")
            continue
        if not configure(sid, cfg["token"]):
            failures += 1
    print("")
    print(f"Done. {failures} falha(s).")
    sys.exit(0 if failures == 0 else 2)


if __name__ == "__main__":
    main()
