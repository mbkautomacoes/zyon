#!/usr/bin/env bash
set -u
cd /home/zyon/zyon
source /home/zyon/zyon/.venv/bin/activate

export CI=true
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="sk-e0fe016817f44cdba42da34a96ac3a5b"
export ANTHROPIC_MODEL="deepseek-v4-pro"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK="1"

FIRST_RUN_FLAG=/home/zyon/zyon/.claude_monitor_started

AGENT_PROMPT="Voce e o agente Zyon do WhatsApp. Processe mensagens NAO processadas:

1. Leia o arquivo messages_session1.jsonl
2. Leia o arquivo processed_ids_session1.txt
3. Para cada mensagem no JSONL cujo ID NAO esta em processed_ids:
   a. Envie uma resposta via: python -m whatsapp_agent.send_message [FROM] '[RESPOSTA]' [SESSION]
   b. Adicione o ID: echo [ID] >> processed_ids_session1.txt
4. Quando terminar, responda DONE."

if [ ! -f "${FIRST_RUN_FLAG}" ]; then
    echo "[loop] First run with full context at $(date)"
    timeout 180 /usr/bin/claude --dangerously-skip-permissions \
        "Leia CLAUDE_PROMPT.md. Depois: ${AGENT_PROMPT}" || true
    touch "${FIRST_RUN_FLAG}"
    echo "[loop] First run complete"
fi

while true; do
    echo "[loop] Checking messages at $(date)"
    pkill -f "whatsapp_agent.monitor" 2>/dev/null || true
    timeout 120 /usr/bin/claude --dangerously-skip-permissions \
        "${AGENT_PROMPT}" || true
    echo "[loop] Cycle done, sleeping 10s..."
    sleep 10
done
