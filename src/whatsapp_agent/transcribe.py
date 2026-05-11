"""
Transcricao de audio via OpenAI Whisper.

Endpoint: POST https://api.openai.com/v1/audio/transcriptions
Modelo:   whisper-1
Aceita:   ogg, mp3, m4a, wav, mp4, webm.

Uso (CLI): python transcribe.py <audio_file>
"""
import json
import os
import subprocess
import sys

from config import OPENAI_API_KEY


WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


def transcribe_audio(path: str) -> str:
    """
    Returns transcript text on success.
    Returns bracketed marker on failure (never raises - keeps message flow alive).
    """
    if not OPENAI_API_KEY:
        return "[audio - transcricao desativada: configure OPENAI_API_KEY em config.py]"
    if not os.path.exists(path):
        return f"[audio - arquivo nao encontrado: {path}]"

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", WHISPER_URL,
                "-H", f"Authorization: Bearer {OPENAI_API_KEY}",
                "-F", "model=whisper-1",
                "-F", f"file=@{path}",
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
    except Exception as e:
        return f"[audio - erro de rede: {e}]"

    if result.returncode != 0:
        detail = (result.stderr or "").strip() or f"curl exit {result.returncode}"
        return f"[audio - erro de rede: {detail}]"

    try:
        data = json.loads(result.stdout)
    except Exception:
        return "[audio - erro: resposta invalida do Whisper]"

    if "error" in data:
        msg = data["error"].get("message", "unknown") if isinstance(data["error"], dict) else str(data["error"])
        return f"[audio - erro: {msg}]"

    return (data.get("text") or "[audio - transcricao vazia]").strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)
    print(transcribe_audio(sys.argv[1]))
