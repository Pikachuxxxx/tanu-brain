#!/bin/bash

# Launch Tanu's Corner Server and ngrok Tunnel
# This script ensures the server stays up and uses any available ngrok tunnel.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Load .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

echo "🏮 Starting Tanu's Corner Server..."
pkill -f tanu_corner_server.py || true
sleep 1
nohup $VENV_PYTHON "$PROJECT_DIR/tanu_corner_server.py" > "$PROJECT_DIR/server.log" 2>&1 &

# Setup ngrok
if command -v ngrok &> /dev/null; then
    echo "🌐 Opening ngrok tunnel..."
    pkill -f ngrok || true
    sleep 1
    
    if [ ! -z "$NGROK_AUTHTOKEN" ]; then
        ngrok config add-authtoken "$NGROK_AUTHTOKEN" > /dev/null 2>&1
    fi

    if [ ! -z "$NGROK_DOMAIN" ]; then
        echo "📍 Using custom domain: $NGROK_DOMAIN"
        nohup ngrok http 8000 --domain="$NGROK_DOMAIN" > "$PROJECT_DIR/ngrok.log" 2>&1 &
    else
        echo "📍 Using ephemeral free URL..."
        nohup ngrok http 8000 > "$PROJECT_DIR/ngrok.log" 2>&1 &
    fi
    
    echo "⏳ Waiting for ngrok to stabilize..."
    sleep 8
    URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.[a-z]*' | head -n 1)
    
    if [ ! -z "$URL" ]; then
        echo "✨ Tanu's Corner is now live at: $URL"
        # Update README immediately with the new URL
        cd "$PROJECT_DIR"
        ./venv/bin/python -c "from tanu_brain import update_readme; update_readme()"
    else
        echo "⚠️ ngrok started but URL not found. Check ngrok.log"
        cat "$PROJECT_DIR/ngrok.log"
    fi
else
    echo "⚠️ ngrok not found. Server is only available at http://localhost:8000"
fi
