# ============================================================
# WhatsApp Claude Agent — Configuration Template
# ============================================================
# Copy this file to `config.py` and fill in your real values.
# DO NOT commit config.py (already in .gitignore).
# ============================================================

# Token legado/opcional. Whitelist (SESSIONS phone) ja restringe quem pode
# disparar o agente. Deixe vazio se nao quiser camada extra.
# Quando definido, voce pode opcionalmente exigir prefixo "!TOKEN " no
# CLAUDE_PROMPT.md (precisa editar manualmente).
CMD_TOKEN = ""

# Assinatura automatica anexada em todas as respostas.
# Tambem usada para quebrar loop (ignora mensagens proprias).
SIGNATURE = "*Claude Code*"

# Host da API WhatsApp (MBKCHAT / WuzAPI)
API_HOST = "https://mbkchat.com.br"

# ------------------------------------------------------------
# Sessoes (usuarios da API)
# ------------------------------------------------------------
# Cada sessao = 1 numero de WhatsApp + 1 token de usuario.
# Para descobrir o LID: envie 1a mensagem do numero, olhe
# raw_debug.jsonl, copie o campo "data.chat" (parte antes
# de @s.whatsapp.net ou @lid).
# ------------------------------------------------------------
SESSIONS = {
    "1": {
        "token":    "SEU_TOKEN_MBKCHAT_AQUI",
        "phone":    "5511999999999",          # numero com DDI+DDD, sem +
        "lid":      "",                       # preencher apos 1a mensagem
    },
    # Para multi-sessao, descomente e configure:
    # "2": {
    #     "token":    "OUTRO_TOKEN",
    #     "phone":    "5511888888888",
    #     "lid":      "",
    # },
}

# ------------------------------------------------------------
# Multimodal (opcional - deixe em branco para desativar)
# ------------------------------------------------------------
# OpenAI Whisper para transcrever audios recebidos.
# Pegue chave: https://platform.openai.com/api-keys
OPENAI_API_KEY = ""

# Defaults derivados (nao alterar)
ALLOWED_PHONE = SESSIONS["1"]["phone"]
ALLOWED_LID   = SESSIONS["1"]["lid"]
API_TOKEN     = SESSIONS["1"]["token"]
