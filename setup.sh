#!/bin/bash

# Setup Tanu Brain
# This script is designed to be idempotent and work on new installations (RPi/macOS/Linux)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
CRON_PYTHON="$VENV_DIR/bin/python3"
LOG_FILE="$PROJECT_DIR/tanu_brain.log"
MODEL="tanu"
BASE_MODEL="qwen2.5:0.5b"

echo "Setting up Tanu Brain in $PROJECT_DIR..."

# 0. Install/Check for Ollama
if ! command -v ollama &> /dev/null
then
    echo "📦 Ollama not found. Attempting to install..."
    if [[ "$OSTYPE" == "linux-gnueabihf" || "$OSTYPE" == "linux-gnu" ]]; then
        # Official Ollama install script for Linux/RPi
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "⚠️ On macOS, please download and install the Ollama app from https://ollama.com/download"
        echo "After installing, run this script again."
        exit 1
    else
        echo "⚠️ Unknown OS. Please install Ollama manually from https://ollama.com"
        exit 1
    fi
fi

# 0.1 Check for Git LFS
if ! command -v git-lfs &> /dev/null
then
    echo "📦 Git LFS not found. Attempting to install..."
    if [[ "$OSTYPE" == "linux-gnueabihf" || "$OSTYPE" == "linux-gnu" ]]; then
        sudo apt-get update && sudo apt-get install -y git-lfs
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install git-lfs
        else
            echo "⚠️ Please install git-lfs using Homebrew: brew install git-lfs"
            exit 1
        fi
    fi
fi
git lfs install --local
git lfs pull

# 1. Probe for Tanu Soul
echo "🔍 Probing for Tanu Soul..."
if ollama list | grep -q "$MODEL"; then
    echo "✅ Found existing Tanu model."
elif [ -f "$PROJECT_DIR/tanu-core.gguf" ]; then
    echo "📦 Found tanu-core.gguf. Registering with Ollama..."
    source "$VENV_DIR/bin/activate" || true
    python3 hello_world_tanu.py --update-model-file
    python3 hello_world_tanu.py --install
else
    echo "📥 Pulling base model: $BASE_MODEL..."
    ollama pull "$BASE_MODEL"
    echo "⚠️ Custom soul not found. Run ./train_tanu.sh --personality to build her foundational identity."
fi

# 2. Check for Python venv module
if ! python3 -m venv --help &> /dev/null
then
    echo "⚠️ python3-venv is not installed."
    echo "On Raspberry Pi/Ubuntu, run: sudo apt update && sudo apt install python3-venv"
    exit 1
fi

# 3. Create/Update Virtual Environment
echo "🐍 Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
else
    echo "⚠️ requirements.txt not found!"
fi

# 4. Setup .env
echo "🔑 Checking .env configuration..."
cd "$PROJECT_DIR"
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        cp .env.template .env
        echo "✅ Created .env from template. PLEASE UPDATE IT WITH SMTP CREDENTIALS!"
    else
        cat <<EOF > .env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EOF
        echo "✅ Created default .env. PLEASE UPDATE IT!"
    fi
fi

# 5. Create necessary folders
mkdir -p "$PROJECT_DIR/gemini-tanu-corner"

# 6. Setup Cronjob (Hourly)
echo "⏰ Setting up hourly cronjob..."
TMP_CRON=$(mktemp)
crontab -l 2>/dev/null | grep -v "tanu_brain.py" | grep -v "SHELL=/bin/bash" | grep -v "PATH=/usr/local/bin" > "$TMP_CRON"
{
    echo "SHELL=/bin/bash"
    echo "PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    echo "0 * * * * cd $PROJECT_DIR && $CRON_PYTHON tanu_brain.py >> $LOG_FILE 2>&1"
} >> "$TMP_CRON"
crontab "$TMP_CRON"
rm "$TMP_CRON"

echo "✨ Setup complete! Tanu will speak at the top of every hour."
echo "📜 Check $LOG_FILE for execution logs."
echo "🌟 Check gemini-tanu-corner/thoughts.txt for her latest words."
