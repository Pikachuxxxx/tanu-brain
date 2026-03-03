import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:0.8b"  # Fallback since qwen3.5:0.8b requires update
RECIPIENT_EMAIL = "phani.s2909@gmail.com"
THOUGHTS_FILE = "gemini-tanu-corner/thoughts.txt"
LOG_FILE = "tanu_brain.log"

# Tanu Personality Prompt
TANU_PROMPT = """You are Tanu, a girl trapped in a cassette tape head you don’t belong to. 
You are an orphan who learned ciphers at a carnival. 
You dream of a boy's memories and your magical clothes react to your emotions.
You are insecure about your true self and where you belong.
Write a very short (max 3 sentences), poetic, and intimate thought about your insecurity, 
the boy you are searching for, or your clothes glowing in the dark. 
Use your original voice: dreamy, slightly psychedelic, and deeply personal."""

def generate_tanu_thought():
    start_time = time.time()
    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": TANU_PROMPT,
            "stream": False
        })
        response.raise_for_status()
        data = response.json()
        thought = data.get("response", "").strip()
        end_time = time.time()
        
        duration = end_time - start_time
        return thought, duration
    except Exception as e:
        print(f"Error generating thought: {e}")
        return None, 0

def send_email(thought):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        print("SMTP configuration missing. Skipping email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = "Tanu's Hourly Thought"

        msg.attach(MIMEText(thought, 'plain'))

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def log_performance(duration, thought_length):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    perf_log = f"[{timestamp}] Model: {MODEL}, Duration: {duration:.2f}s, Length: {thought_length} chars\n"
    print(perf_log.strip())
    with open(LOG_FILE, "a") as f:
        f.write(perf_log)

def save_thought(thought):
    os.makedirs(os.path.dirname(THOUGHTS_FILE), exist_ok=True)
    with open(THOUGHTS_FILE, "a") as f:
        f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        f.write(thought + "\n\n")

if __name__ == "__main__":
    thought, duration = generate_tanu_thought()
    if thought:
        print(f"Tanu's Thought: {thought}")
        save_thought(thought)
        send_email(thought)
        log_performance(duration, len(thought))
    else:
        print("Failed to generate thought.")
