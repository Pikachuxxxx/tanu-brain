#!/bin/bash

# Setup Tanu Brain
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
CRON_PYTHON="$VENV_DIR/bin/python3"
LOG_FILE="$PROJECT_DIR/tanu_brain.log"

# Check if ollama is installed
if ! command -v ollama &> /dev/null
then
    echo "Ollama is not installed. Please install it from https://ollama.com"
    exit 1
fi

echo "Setting up Tanu Brain in $PROJECT_DIR..."

# 1. Create venv
if ! python3 -m venv --help &> /dev/null
then
    echo "python3-venv is not installed. On RPi/Ubuntu, run: sudo apt install python3-venv"
    exit 1
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2. Setup .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        cp .env.template .env
        echo "PLEASE UPDATE .env WITH YOUR SMTP CREDENTIALS!"
    else
        touch .env
        echo "SMTP_SERVER=smtp.gmail.com" >> .env
        echo "SMTP_PORT=587" >> .env
        echo "SMTP_USER=your-email@gmail.com" >> .env
        echo "SMTP_PASSWORD=your-app-password" >> .env
        echo "Created .env file. PLEASE UPDATE IT!"
    fi
fi

# 3. Create necessary folders
mkdir -p gemini-tanu-corner

# 4. Setup Cronjob
# We include SHELL and PATH to ensure cron can find ollama and run correctly on macOS
(crontab -l 2>/dev/null | grep -v "tanu_brain.py"; 
 echo "SHELL=/bin/bash";
 echo "PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin";
 echo "0 * * * * cd $PROJECT_DIR && $CRON_PYTHON tanu_brain.py >> $LOG_FILE 2>&1") | crontab -

echo "Setup complete. Tanu will think every hour."
echo "Check $LOG_FILE for activity."
