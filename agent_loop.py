#!/usr/bin/env python3
"""Zyon 24/7 agent loop — polls JSONL and replies via DeepSeek API directly."""

import json
import os
import sys
import time
import requests

# --- Config ---
SESSION = sys.argv[1] if len(sys.argv) > 1 else "1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSONL_FILE = os.path.join(BASE_DIR, f"messages_session{SESSION}.jsonl")
PROCESSED_FILE = os.path.join(BASE_DIR, f"processed_ids_session{SESSION}.txt")

DEEPSEEK_URL = "https://api.deepseek.com/anthropic/v1/messages"
DEEPSEEK_TOKEN = "sk-e0fe016817f44cdba42da34a96ac3a5b"
DEEPSEEK_MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """Voce e o Zyon, um assistente pessoal via WhatsApp operado pela MBK Automações.

Regras:
- Responda em português do Brasil, tom amigável e direto.
- Use Markdown simples (negrito, listas) quando apropriado.
- Mantenha respostas concisas (máximo 4000 caracteres).
- Não mencione que é um bot ou IA a menos que perguntado diretamente.
- Seu criador é Manoel, da MBK Automações.
- Assuma que você está falando com Manoel (self-chat) a menos que indicado de outra forma."""

# --- Helpers ---

def load_jsonl(path):
    """Load all lines from a JSONL file."""
    if not os.path.exists(path):
        return []
    messages = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return messages


def load_processed_ids(path):
    """Load set of already-processed message IDs."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(path, msg_id):
    """Append a message ID to the processed file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{msg_id}\n")


def call_deepseek(user_message, history=None):
    """Call DeepSeek API (Anthropic-compatible) to generate a reply."""
    headers = {
        "x-api-key": DEEPSEEK_TOKEN,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    messages = [{"role": "user", "content": user_message}]

    payload = {
        "model": DEEPSEEK_MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }

    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        print(f"[agent] DeepSeek API error: {resp.status_code} {resp.text[:200]}", flush=True)
        return None

    data = resp.json()
    return data.get("content", [{}])[0].get("text", "")


def send_reply(phone, text, session):
    """Send a WhatsApp reply via send_message.py."""
    import subprocess
    # Strip problematic characters for shell
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    cmd = [
        sys.executable, "-m", "whatsapp_agent.send_message",
        phone, safe_text, session,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=BASE_DIR)
        if result.returncode != 0:
            print(f"[agent] send_message error: {result.stderr[:200]}", flush=True)
            return False
        return True
    except Exception as e:
        print(f"[agent] send_message exception: {e}", flush=True)
        return False


# --- Main Loop ---

def main():
    print(f"[agent] Zyon agent loop started for session {SESSION}", flush=True)
    print(f"[agent] JSONL: {JSONL_FILE}", flush=True)
    print(f"[agent] Processed: {PROCESSED_FILE}", flush=True)

    while True:
        try:
            messages = load_jsonl(JSONL_FILE)
            processed = load_processed_ids(PROCESSED_FILE)

            pending = [m for m in messages if m.get("id") not in processed]

            if pending:
                print(f"[agent] Found {len(pending)} pending message(s)", flush=True)
                for msg in pending:
                    msg_id = msg.get("id", "")
                    phone = msg.get("from", "")
                    text = msg.get("text", "")
                    name = msg.get("name", "")
                    session = msg.get("session", SESSION)

                    print(f"[agent] Processing {msg_id}: {text[:80]}", flush=True)

                    # Generate reply via DeepSeek
                    reply = call_deepseek(text)
                    if not reply:
                        reply = "Desculpe, não consegui processar sua mensagem. Tente novamente."

                    print(f"[agent] Reply: {reply[:80]}...", flush=True)

                    # Send reply
                    if send_reply(phone, reply, session):
                        mark_processed(PROCESSED_FILE, msg_id)
                        print(f"[agent] Sent and marked {msg_id}", flush=True)
                    else:
                        print(f"[agent] Failed to send reply for {msg_id}", flush=True)
            else:
                pass  # No pending messages, silent

        except Exception as e:
            print(f"[agent] Loop error: {e}", flush=True)

        time.sleep(5)


if __name__ == "__main__":
    main()
