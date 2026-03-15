#!/bin/bash

# Uninstall Tanu Bot
PROJECT_DIR="$(pwd)"

echo "Uninstalling Tanu Bot..."

# 1. Stop all processes
if [ -f "./kill_all.sh" ]; then
    ./kill_all.sh
fi

# 2. Remove Cronjob
(crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/tanu_brain.py") | crontab -
echo "Cronjob removed."

# 2. Cleanup (optional)
echo "You can now safely delete the directory: $PROJECT_DIR"
echo "To delete everything, run: cd .. && rm -rf tanu-bot"
