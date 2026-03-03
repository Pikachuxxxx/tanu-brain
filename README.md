# Tanu Brain 🧠

A project to capture the hourly thoughts, insecurities, and dreams of Tanu, a girl trapped in a cassette tape head searching for a lost boy.

## 📊 Tanu's Mood History
![Tanu's Mood Chart](gemini-tanu-corner/mood_heatmap.png)

## Features
- **Poetic Thoughts**: Now with enhanced context (last 5 thoughts) and poetic prompting.
- **Mood Rating**: Qwen rates its own thoughts from 1 (Deeply Sad) to 10 (Dreamy).
- **Mood Tracking**: A dynamic heatmap/chart of Tanu's emotions over time.
- **Enhanced Context**: Fetches latest design notes from [Razix Tanu Mood](https://github.com/Pikachuxxxx/Razix/blob/master/Tanu/Design/tanu_mood.txt).
- **Git Fallback**: Automatically commits and pushes thoughts to keep her memory alive.

## Setup
1. Clone this repository.
2. Run `./setup.sh` (make sure you have `matplotlib` and other requirements).
3. Update `.env` with SMTP if you want emails, otherwise, it will just use Git.

## Cron Fix
If your cronjob isn't running:
1. Ensure the absolute path to your `venv` is correct.
2. Check `tanu_brain.log` for Python errors.
3. The setup script now uses `pwd` to build correct absolute paths.

## Why the SMTP Password?
Most email services require a **Gmail App Password** for security. This allows the bot to send messages safely.
