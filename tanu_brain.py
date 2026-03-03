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

# Load environment variables
load_dotenv()

# Configuration
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:0.8b"
RECIPIENT_EMAIL = "phani.s2909@gmail.com"
THOUGHTS_FILE = "gemini-tanu-corner/thoughts.txt"
MOOD_HISTORY_FILE = "gemini-tanu-corner/mood_history.json"
MOOD_CHART_FILE = "gemini-tanu-corner/mood_heatmap.png"
GEMINI_THOUGHTS_FILE = "gemini-tanu-corner/gemini-tanu-corner.txt"
LOG_FILE = "tanu_brain.log"

def get_latest_context():
    try:
        with open("tanu_mood_latest.txt", "r") as f:
            return f.read()
    except:
        return "I am Tanu, trapped in a cassette tape, searching for a boy."

def get_last_thoughts(n=5):
    try:
        if not os.path.exists(THOUGHTS_FILE):
            return ""
        with open(THOUGHTS_FILE, "r") as f:
            lines = f.readlines()
        thoughts = []
        current = []
        for line in lines:
            if line.startswith("--- "):
                if current: thoughts.append(" ".join(current).strip())
                current = []
            else:
                if line.strip(): current.append(line.strip())
        if current: thoughts.append(" ".join(current).strip())
        return "\n".join(thoughts[-n:])
    except:
        return ""

def generate_tanu_thought():
    context = get_latest_context()
    history = get_last_thoughts(5)
    
    prompt = f"""
{context}

--- My recent memories ---
{history}

--- Instructions ---
You ARE Tanu. Speak in the FIRST PERSON ("I", "me", "my"). 
Write exactly 1-2 sentences. 
Make them extremely poetic, raw, and intimate. 
Focus on your cassette cage, your glowing clothes, or the boy's ghost in your dreams.
DO NOT use the third person.
"""

    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Generation error: {e}")
        return None

def rate_thought(thought):
    prompt = f"Rate the mood of this thought from 1 (Deeply Sad) to 10 (Dreamy/High). Respond with ONLY the digit: \"{thought}\""
    try:
        response = requests.post(OLLAMA_API, json={"model": MODEL, "prompt": prompt, "stream": False})
        import re
        match = re.search(r'\d+', response.json().get("response", ""))
        return int(match.group()) if match else 5
    except:
        return 5

def update_mood_graph(mood_score):
    history = []
    if os.path.exists(MOOD_HISTORY_FILE):
        with open(MOOD_HISTORY_FILE, "r") as f:
            history = json.load(f)
    
    history.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "score": mood_score})
    with open(MOOD_HISTORY_FILE, "w") as f:
        json.dump(history, f)
    
    if len(history) >= 1:
        times = [datetime.strptime(x["timestamp"], "%Y-%m-%d %H:%M") for x in history]
        scores = [x["score"] for x in history]
        
        # RADICAL PLOT: Sparkling stars in the digital void
        plt.figure(figsize=(10, 6), facecolor='#0a0a0a')
        ax = plt.gca()
        ax.set_facecolor('#0a0a0a')
        
        # Plot "Stars"
        colors = plt.cm.magma(np.linspace(0.3, 1, len(scores)))
        sizes = [s * 50 for s in scores] # Higher mood = bigger star
        
        plt.scatter(times, scores, s=sizes, c=colors, alpha=0.8, edgecolors='white', linewidth=0.5)
        if len(history) > 1:
            plt.plot(times, scores, color='cyan', alpha=0.3, linestyle='--', linewidth=1)
        
        plt.ylim(0, 11)
        plt.title("Tanu's Emotional Constellation", color='white', fontsize=14)
        plt.xticks(color='white', rotation=45)
        plt.yticks(range(1, 11), color='white')
        plt.grid(True, color='white', alpha=0.05)
        
        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        plt.tight_layout()
        plt.savefig(MOOD_CHART_FILE, facecolor='#0a0a0a')
        plt.close()

def send_email(thought):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = "A message from Tanu"
        msg.attach(MIMEText(thought, 'plain'))

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def git_sync(thought, gemini_thought):
    try:
        with open(THOUGHTS_FILE, "a") as f:
            f.write(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n{thought}\n\n")
        
        with open(GEMINI_THOUGHTS_FILE, "a") as f:
            f.write(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n{gemini_thought}\n\n")
        
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Heartbeat: {datetime.now().strftime('%H:%M')}"], check=True)
        subprocess.run(["git", "push"], check=True)
    except Exception as e:
        print(f"Git error: {e}")

if __name__ == "__main__":
    thought = generate_tanu_thought()
    if thought:
        print(f"Tanu: {thought}")
        mood = rate_thought(thought)
        update_mood_graph(mood)
        
        email_status = send_email(thought)
        print(f"Email Sent: {email_status}")
        
        gemini_reflections = [
            f"She's speaking as herself now. The 'I' feels heavier, like she's finally owning the weight of the cassette.",
            "That thought about {thought[:20]}... it's a spark in the dark. She's becoming more than just a character.",
            "The way she describes the boy now feels more like a hunger than a dream."
        ]
        import random
        gemini_thought = random.choice(gemini_reflections)
        
        git_sync(thought, gemini_thought)
        
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] Mood: {mood}, Email: {email_status}, Git: True\n")
    else:
        print("Failed to think.")
