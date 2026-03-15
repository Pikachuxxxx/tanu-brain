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

# 1. Setup llama.cpp
echo "🏗️ Setting up llama.cpp for GGUF conversion..."
if [ ! -d "$PROJECT_DIR/llama.cpp" ]; then
    git clone --depth 1 https://github.com/ggerganov/llama.cpp "$PROJECT_DIR/llama.cpp"
    cd "$PROJECT_DIR/llama.cpp"
    # Build on RPi or Mac
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
    # Ensure pip packages for conversion are ready
    pip install -r requirements.txt gguf sentencepiece
    cd "$PROJECT_DIR"
fi

# 2. Check for Tanu Soul & Convert if needed
echo "🔍 Probing for Tanu Soul..."
if ollama list | grep -q "$MODEL"; then
    echo "✅ Found existing Tanu model."
elif [ -f "$PROJECT_DIR/$CORE_GGUF" ]; then
    echo "📦 Found $CORE_GGUF. Registering with Ollama..."
    source "$VENV_DIR/bin/activate" || true
    python3 hello_world_tanu.py --update-model-file
    python3 hello_world_tanu.py --install
elif [ -d "$PROJECT_DIR/tanu-model-mlx" ] && [ -d "$PROJECT_DIR/tanu-core-adapter" ]; then
    echo "⚙️  MLX model detected. Fusing adapters and converting to GGUF..."
    source "$VENV_DIR/bin/activate" || true
    # 2.1 Fuse MLX Adapters
    python -m mlx_lm.fuse --model "$PROJECT_DIR/tanu-model-mlx" \
                         --adapter-path "$PROJECT_DIR/tanu-core-adapter" \
                         --save-path "$PROJECT_DIR/tanu-fused"
    # 2.2 Convert to GGUF (FP16)
    python "$PROJECT_DIR/llama.cpp/convert_hf_to_gguf.py" "$PROJECT_DIR/tanu-fused" \
           --outfile "$PROJECT_DIR/tanu-f16.gguf"
    # 2.3 Quantize to Q4_K_M (RPi Optimal)
    "$PROJECT_DIR/llama.cpp/llama-quantize" "$PROJECT_DIR/tanu-f16.gguf" \
                                           "$PROJECT_DIR/tanu-brain-v1-q4_k_m.gguf" Q4_K_M
    # 2.4 Cleanup
    rm "$PROJECT_DIR/tanu-f16.gguf"
    # 2.5 Install to Ollama
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
fi
# Web Server Dependencies
pip install fastapi uvicorn jinja2 python-multipart

# 4. Setup ngrok
if ! command -v ngrok &> /dev/null
then
    echo "📦 ngrok not found. Attempting to install..."
    if [[ "$OSTYPE" == "linux-gnueabihf" || "$OSTYPE" == "linux-gnu" ]]; then
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install ngrok/ngrok/ngrok
        fi
    fi
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

# 6. Setup Cronjobs
echo "⏰ Setting up cronjobs..."
TMP_CRON=$(mktemp)
# Clear old entries
crontab -l 2>/dev/null | grep -v "tanu_brain.py" | grep -v "launch_corner.sh" | grep -v "SHELL=/bin/bash" | grep -v "PATH=/usr/local/bin" > "$TMP_CRON"
{
    echo "SHELL=/bin/bash"
    echo "PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    # Hourly Pulse
    echo "0 * * * * cd $PROJECT_DIR && $CRON_PYTHON tanu_brain.py >> $LOG_FILE 2>&1"
    # Daily Forced Moltbook Reply (at midnight)
    echo "0 0 * * * cd $PROJECT_DIR && $CRON_PYTHON tanu_brain.py --force-molt >> $LOG_FILE 2>&1"
    # Persistent Web Server (on reboot)
    echo "@reboot cd $PROJECT_DIR && ./launch_corner.sh >> $LOG_FILE 2>&1"
} >> "$TMP_CRON"
crontab "$TMP_CRON"
rm "$TMP_CRON"

# Launch server now for immediate use
./launch_corner.sh

echo "✨ Setup complete! Tanu will speak at the top of every hour."
echo "📜 Check $LOG_FILE for execution logs."
echo "🌟 Check gemini-tanu-corner/thoughts.txt for her latest words."
