#!/usr/bin/env bash
# Stops webhook server (tunnel roda como service separado)
echo "Stopping webhook..."
pkill -f "whatsapp_agent.webhook_server\|webhook_server.py" 2>/dev/null || true
rm -f .webhook.pid
echo "Stopped."
