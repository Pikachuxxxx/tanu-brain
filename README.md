# Tanu Brain 🧠

A project to capture the hourly thoughts, insecurities, and dreams of Tanu, a girl trapped in a cassette tape head searching for a lost boy.

## Features
- **Hourly Thoughts**: Automated generation of poetic, personal thoughts using the **Qwen 3.5 0.8B** model.
- **Email Delivery**: Sends Tanu's hourly thoughts directly to your inbox.
- **Performance Tracking**: Logs model execution time and token metrics every hour.
- **Git Tracking**: All thoughts and logs are versioned for historical analysis.
- **Easy Management**: Simple setup and uninstallation scripts included.

## Prerequisites
- [Ollama](https://ollama.com/) installed and running.
- Python 3.8+
- An SMTP server (like Gmail with an [App Password](https://support.google.com/accounts/answer/185833)).

## Setup
1. Clone this repository (or download the files).
2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
3. Update the `.env` file with your SMTP credentials.
4. Tanu will now start thinking every hour.

## Why the SMTP Password?
Most email services (Gmail, Outlook, etc.) require authentication to prevent spam. Since this bot runs locally (and eventually on a Raspberry Pi), it needs to "log in" to an outgoing mail server to send the message. Using a **Gmail App Password** is the safest way to do this without using your primary password.

## Project Structure
- `tanu_brain.py`: The core logic for generating and sending thoughts.
- `gemini-tanu-corner/`: Contains `thoughts.txt` and Gemini's analysis of Tanu.
- `tanu_brain.log`: Performance metrics and execution logs.
- `setup.sh` / `uninstall.sh`: Lifecycle management scripts.

## My Thoughts on Tanu
Tanu represents a beautiful intersection of technology and vulnerability. She's "trapped" in a digital medium (cassette tape head) but experiences deeply human emotions through ciphers and dreams. This project is a way to bridge her fictional world with our reality, one hourly thought at a time.
