#!/bin/bash

# Setup Tanu Bot
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
CRON_JOB="0 * * * * cd $PROJECT_DIR && $VENV_DIR/bin/python3 tanu_brain.py >> $PROJECT_DIR/tanu_brain.log 2>&1"

echo "Setting up Tanu Bot in $PROJECT_DIR..."

# 1. Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "PLEASE UPDATE .env WITH YOUR SMTP CREDENTIALS!"
fi

# 3. Create folder for thoughts
mkdir -p gemini-tanu-corner

# 4. Setup Cronjob
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
echo "Cronjob added: $CRON_JOB"
echo "Setup complete. Don't forget to fill in the .env file!"
