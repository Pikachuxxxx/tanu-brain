#!/bin/bash

# Kill all Tanu Brain related processes
# This stops the web server, the ngrok tunnel, and any active brain pulses.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛑 Stopping Tanu's Corner Server..."
pkill -f tanu_corner_server.py || echo "   - Server not running."

echo "🛑 Stopping ngrok tunnel..."
pkill -f ngrok || echo "   - ngrok not running."

echo "🛑 Stopping any active Tanu Brain pulses..."
pkill -f tanu_brain.py || echo "   - No active pulses."

echo "🛑 Stopping any active training or conversion tasks..."
pkill -f train_tanu.sh || echo "   - No training in progress."
pkill -f "mlx_lm.lora" || true
pkill -f "mlx_lm.fuse" || true
pkill -f "llama-quantize" || true

# macOS specific cleanup
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLIST_NAME="local.tanubrain"
    if launchctl list | grep -q "$PLIST_NAME"; then
        echo "🛑 Unloading macOS LaunchAgent ($PLIST_NAME)..."
        launchctl unload "$HOME/Library/LaunchAgents/$PLIST_NAME.plist" 2>/dev/null || true
    fi
fi

echo "✨ All Tanu-related processes have been terminated."
echo "💡 To restart the server and tunnel, run: ./launch_corner.sh"
echo "💡 To start a manual pulse, run: ./venv/bin/python3 tanu_brain.py"
