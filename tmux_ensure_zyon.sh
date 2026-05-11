#!/usr/bin/env bash
set -u
SESSION=zyon
if tmux has-session -t "$SESSION" 2>/dev/null; then
    exit 0
fi
tmux new-session -d -s "$SESSION" -c /home/zyon/zyon \
    "/home/zyon/zyon/scripts/claude_monitor_loop.sh"
echo "tmux session zyon started"
