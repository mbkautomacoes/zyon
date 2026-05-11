"""Monitor messages_sessionX.jsonl — emite novas mensagens reais.
Uso: python monitor.py [session]   (default: 1)
"""
import time
import os
import sys
import json

from config import SIGNATURE

SESSION       = sys.argv[1] if len(sys.argv) > 1 else "1"
MESSAGES_FILE = f"messages_session{SESSION}.jsonl"
PROCESSED_FILE = f"processed_ids_session{SESSION}.txt"


def load_processed() -> set:
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(msg_id: str):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(msg_id + "\n")


def tail():
    while not os.path.exists(MESSAGES_FILE):
        time.sleep(0.5)

    processed = load_processed()

    with open(MESSAGES_FILE, encoding="utf-8") as f:
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except Exception:
                continue

            msg_id = msg.get("id", "")
            text = msg.get("text", "")

            # ignorar: sem id, já processado, mídia, ou própria resposta
            if not msg_id:
                continue
            if msg_id in processed:
                continue
            if not text or "[m" in text:
                mark_processed(msg_id)
                continue
            if SIGNATURE in text:
                mark_processed(msg_id)
                continue

            mark_processed(msg_id)
            processed.add(msg_id)
            print(line, flush=True)


if __name__ == "__main__":
    tail()
