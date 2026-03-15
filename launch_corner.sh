#!/bin/bash

# Launch Tanu's Corner Server and ngrok Tunnel
# This script is designed to run in the background.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

echo "🏮 Starting Tanu's Corner Server..."
# Run server in background
nohup $VENV_PYTHON "$PROJECT_DIR/tanu_corner_server.py" > "$PROJECT_DIR/server.log" 2>&1 &

# Optional: Start ngrok if a token is configured, otherwise just local
if command -v ngrok &> /dev/null; then
    echo "🌐 Opening ngrok tunnel on port 8000..."
    # We use --log=stdout to check if it started correctly, then move to background
    nohup ngrok http 8000 > "$PROJECT_DIR/ngrok.log" 2>&1 &
    sleep 2
    URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.app')
    echo "✨ Tanu's Corner is now live at: $URL"
else
    echo "⚠️ ngrok not found. Server is only available at http://localhost:8000"
fi
