#!/usr/bin/env bash
# ============================================================
# WhatsApp Claude Agent — Linux/macOS installer
# ============================================================
# Run from project root:
#   chmod +x install.sh && ./install.sh
# ============================================================

set -e

echo ""
echo "=== WhatsApp Claude Agent - Install ==="
echo ""

# --- 1. Check Python ---
echo "[1/5] Checking Python..."
if command -v python3 >/dev/null 2>&1; then
    echo "  OK: $(python3 --version)"
else
    echo "  ERROR: python3 not found. Install Python 3.8+"
    exit 1
fi

# --- 2. Check curl ---
echo "[2/5] Checking curl..."
if command -v curl >/dev/null 2>&1; then
    echo "  OK: curl available"
else
    echo "  ERROR: curl not found. Install via: apt install curl  (or brew install curl)"
    exit 1
fi

# --- 3. Check ngrok ---
echo "[3/5] Checking ngrok..."
if command -v ngrok >/dev/null 2>&1; then
    echo "  OK: ngrok in PATH"
else
    echo "  WARNING: ngrok not found. Download: https://ngrok.com/download"
    echo "  After install, run: ngrok config add-authtoken <YOUR_TOKEN>"
fi

# --- 4. Run interactive config wizard ---
echo "[4/5] Configuring..."
python3 setup_config.py
if [ $? -ne 0 ]; then
    echo "  ERROR: config wizard failed."
    exit 1
fi

# --- 5. Done ---
echo "[5/5] Install complete."
echo ""
echo "Next steps:"
echo "  1. Run:    ./start.sh"
echo "  2. Paste the ngrok URL shown into megaAPI webhook config"
echo "  3. Send WhatsApp message to yourself"
echo "  4. Run:    python3 discover_lid.py    (auto-fills LID)"
echo "  5. Open Claude Code and follow CLAUDE_PROMPT.md"
echo "  - If anything breaks: python3 doctor.py"
echo ""
