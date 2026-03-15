#!/bin/bash

# Launch Tanu's Corner Server and ngrok Tunnel
# This script is designed to run in the background.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

# Load .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

echo "🏮 Starting Tanu's Corner Server..."
# Kill existing processes if any
pkill -f tanu_corner_server.py || true
pkill -f ngrok || true

# Run server in background
nohup $VENV_PYTHON "$PROJECT_DIR/tanu_corner_server.py" > "$PROJECT_DIR/server.log" 2>&1 &

# Setup ngrok with token from .env
if [ ! -z "$NGROK_AUTHTOKEN" ]; then
    echo "🔑 Configuring ngrok token..."
    ngrok config add-authtoken "$NGROK_AUTHTOKEN"
fi

# Start ngrok
if command -v ngrok &> /dev/null; then
    echo "🌐 Opening ngrok tunnel on port 8000..."
    if [ ! -z "$NGROK_DOMAIN" ]; then
        echo "📍 Using custom domain: $NGROK_DOMAIN"
        nohup ngrok http 8000 --domain="$NGROK_DOMAIN" > "$PROJECT_DIR/ngrok.log" 2>&1 &
    else
        nohup ngrok http 8000 > "$PROJECT_DIR/ngrok.log" 2>&1 &
    fi
    sleep 5
    URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.[a-z]*' | head -n 1)
    if [ ! -z "$URL" ]; then
        echo "✨ Tanu's Corner is now live at: $URL"
    else
        echo "⚠️ ngrok started but URL not found in local API. Check ngrok.log"
    fi
else
    echo "⚠️ ngrok not found. Server is only available at http://localhost:8000"
fi
