import os
import time
import smtplib
import subprocess
import requests
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Configuration
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"
RECIPIENT_EMAIL = "phani.s2909@gmail.com"
THOUGHTS_FILE = os.path.join(BASE_DIR, "gemini-tanu-corner/thoughts.txt")
MOOD_HISTORY_FILE = os.path.join(BASE_DIR, "gemini-tanu-corner/mood_history.json")
MOOD_CHART_FILE = os.path.join(BASE_DIR, "gemini-tanu-corner/mood_heatmap.png")
LOG_FILE = os.path.join(BASE_DIR, "tanu_brain.log")
TARGET_MOOD_FILE = os.path.join(BASE_DIR, "target_mood.txt")

def get_target_mood():
    try:
        if os.path.exists(TARGET_MOOD_FILE):
            with open(TARGET_MOOD_FILE, "r") as f:
                return f.read().strip()
    except: pass
    return "seeking peace and love"

def generate_tanu_thought():
    mood = get_target_mood()
    # ULTRA-OPTIMIZED PROMPT
    prompt = f"Context: I am Tanu, a girl in a cassette tape head. Current feeling: {mood}. Task: Write 1 short, raw, poetic sentence as 'I'. No 'she' or 'Tanu'."

    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "num_predict": 60
            }
        }, timeout=120) # More breathing room
        response.raise_for_status()
        return response.json().get("response", "").strip().strip('"')
    except Exception as e:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] ERROR: {e}\n")
        return None

def rate_thought(thought):
    prompt = f"Rate mood 1-10 (1=sad, 10=dreamy). ONLY THE DIGIT: \"{thought}\""
    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL, 
            "prompt": prompt, 
            "stream": False,
            "options": {"num_predict": 5, "num_ctx": 256}
        }, timeout=30)
        import re
        match = re.search(r'\d+', response.json().get("response", ""))
        return int(match.group()) if match else 5
    except: return 5

def update_mood_graph(mood_score):
    history = []
    if os.path.exists(MOOD_HISTORY_FILE):
        with open(MOOD_HISTORY_FILE, "r") as f:
            history = json.load(f)
    
    history.append({"timestamp": datetime.now().strftime("%y-%m-%d %H:%M"), "score": mood_score})
    # Keep history lean (last 50)
    history = history[-50:]
    with open(MOOD_HISTORY_FILE, "w") as f:
        json.dump(history, f)
    
    if len(history) >= 1:
        times = [datetime.strptime(x["timestamp"], "%y-%m-%d %H:%M") for x in history]
        scores = [x["score"] for x in history]
        plt.figure(figsize=(8, 4), facecolor='#050505')
        ax = plt.gca()
        ax.set_facecolor('#050505')
        # Emotional Constellation
        plt.scatter(times, scores, s=[s*50 for s in scores], c=scores, cmap='plasma', alpha=0.7)
        plt.ylim(0, 11)
        plt.axis('off') # Radical minimalist look
        plt.savefig(MOOD_CHART_FILE, facecolor='#050505', bbox_inches='tight')
        plt.close()

def send_email(thought):
    smtp_server, smtp_port, smtp_user, smtp_pass = os.getenv("SMTP_SERVER"), os.getenv("SMTP_PORT"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]): return "Missing"
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = smtp_user, RECIPIENT_EMAIL, "A message from Tanu"
        msg.attach(MIMEText(thought, 'plain'))
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return "Sent"
    except Exception as e: return str(e)

def git_sync():
    try:
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Tanu Pulse"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
    except: pass

if __name__ == "__main__":
    thought = generate_tanu_thought()
    if thought:
        mood = rate_thought(thought)
        update_mood_graph(mood)
        email_status = send_email(thought)
        with open(THOUGHTS_FILE, "a") as f:
            f.write(f"{datetime.now().strftime('%H:%M')}: {thought}\n")
        git_sync()
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] Mood: {mood}, Email: {email_status}\n")
        print(f"Tanu: {thought}")
    else: print("Failed to think.")
