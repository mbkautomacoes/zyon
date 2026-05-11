#!/usr/bin/env bash
# ============================================================
# WhatsApp Claude Agent — Linux/macOS starter
# ============================================================
# Cloudflare Tunnel deve rodar como servico/daemon separado
# (cloudflared service install). Este script so cuida do webhook.
# URL publica vem de config.PUBLIC_WEBHOOK_URL.
# ============================================================

set -e

if [ ! -f "config.py" ]; then
    echo "ERROR: config.py not found. Run ./install.sh first."
    exit 1
fi

PUBLIC_URL=$(python3 -c "from config import PUBLIC_WEBHOOK_URL; print(PUBLIC_WEBHOOK_URL)" 2>/dev/null || echo "")

echo ""
echo "=== WhatsApp Claude Agent - Start ==="
echo ""

# --- Kill old webhook ---
echo "[1/2] Cleaning old webhook + legacy ngrok..."
pkill -f "whatsapp_agent.webhook_server\|webhook_server.py" 2>/dev/null || true
pkill -f "ngrok http 3020"           2>/dev/null || true
sleep 1

# --- Start webhook server ---
echo "[2/2] Starting webhook server on :3020..."
nohup python3 -m whatsapp_agent.webhook_server > webhook.log 2> webhook.err.log &
echo $! > .webhook.pid
sleep 2

echo ""
echo "=== READY ==="
echo ""
if [ -n "$PUBLIC_URL" ]; then
    echo "Webhook URL publica (config.PUBLIC_WEBHOOK_URL):"
    echo "  $PUBLIC_URL/?session=1"
    echo "  $PUBLIC_URL/?session=2"
else
    echo "WARNING: config.PUBLIC_WEBHOOK_URL vazio."
fi
echo ""
echo "Cloudflare Tunnel: rode 'cloudflared service install' uma vez"
echo "  ou: cloudflared tunnel --config ~/.cloudflared/config.yml run whatsapp-webhook"
echo ""
echo "Apos alterar PUBLIC_WEBHOOK_URL: python3 -m whatsapp_agent.update_webhooks"
echo ""
echo "Next: in Claude Code session, set Monitor to:"
echo "  python3 -m whatsapp_agent.monitor 1"
echo ""
echo "Logs: webhook.log / webhook.err.log"
echo "Stop: ./stop.sh"
