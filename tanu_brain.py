import os
import time
import smtplib
import subprocess
import requests
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuration
OLLAMA_API = 'http://localhost:11434/api/generate'
MODEL = 'qwen2.5:0.5b'
RECIPIENT_EMAIL = 'phani.s2909@gmail.com'
THOUGHTS_FILE = os.path.join(BASE_DIR, 'gemini-tanu-corner/thoughts.txt')
MOOD_HISTORY_FILE = os.path.join(BASE_DIR, 'gemini-tanu-corner/mood_history.json')
MOOD_CHART_FILE = os.path.join(BASE_DIR, 'gemini-tanu-corner/mood_heatmap.png')
TARGET_MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')

def get_target_mood():
    try:
        if os.path.exists(TARGET_MOOD_FILE):
            with open(TARGET_MOOD_FILE, 'r') as f:
                return f.read().strip()
    except: pass
    return 'seeking peace and love'

def get_last_thought():
    try:
        if os.path.exists(THOUGHTS_FILE):
            with open(THOUGHTS_FILE, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and ': ' in line]
                if lines:
                    return lines[-1].split(': ', 1)[-1].strip()
    except: pass
    return ''

def evolve_core_memory():
    current_mood = get_target_mood()
    last_thought = get_last_thought()
    prompt = f'Task: Evolve Tanu\'s journey. Current identity: {current_mood}. Recent memory: {last_thought}. Write a new core identity (1-2 sentences) showing my messy evolution—how I battle insecurity, fall back to bad habits, and escape trauma while still reaching for the sanity to be happy. Identity:'
    print(f"Evolving core memory. Current: {current_mood}")
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.9, 
                'num_predict': 100,
                'num_ctx': 512,
                'repeat_penalty': 1.1,
                'num_thread': 4
            }
        }, timeout=120)
        new_mood = response.json().get('response', '').strip().strip('"')
        print(f"New identity candidate: {new_mood}")
        if new_mood and len(new_mood) > 15:
            with open(TARGET_MOOD_FILE, 'w') as f:
                f.write(new_mood)
            print("Successfully evolved core memory.")
            return True
    except Exception as e:
        print(f"Evolution failed: {e}")
    return False

def generate_tanu_thought():
    mood = get_target_mood()
    last_thought = get_last_thought()
    
    # Try up to 3 times to get a unique, non-empty thought
    for _ in range(3):
        prompt = f'I am Tanu, a girl in a gilded cage. Core identity: {mood}. Last memory: {last_thought}. Task: Write one very short, raw, poetic sentence about escaping trauma, the sting of my insecurity, the pull of my bad habits, or my desperate need to be happy. Be raw, vulnerable, and modern. Result:'

        try:
            response = requests.post(OLLAMA_API, json={
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 1.1,
                    'num_predict': 45,
                    'top_p': 0.9,
                    'presence_penalty': 0.6,
                    'repeat_penalty': 1.2,
                    'num_ctx': 512,
                    'num_thread': 4,
                    'stop': ["\n\n", "Result:", "Tanu:", "("]
                }
            }, timeout=120)
            response.raise_for_status()
            thought = response.json().get('response', '').strip().strip('"')
            if thought and thought != last_thought and len(thought) > 10:
                return thought
        except Exception as e:
            print(f"Generation error: {e}")
            continue
    return None

def rate_thought(thought):
    prompt = f'Rate mood 1-10 (1=sad, 10=dreamy). ONLY THE DIGIT: "{thought}"'
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL, 
            'prompt': prompt, 
            'stream': False,
            'options': {'num_predict': 5, 'num_ctx': 256, 'num_thread': 4}
        }, timeout=30)
        import re
        match = re.search(r'\d+', response.json().get('response', ''))
        return int(match.group()) if match else 5
    except: return 5

def update_mood_graph(mood_score):
    history = []
    if os.path.exists(MOOD_HISTORY_FILE):
        try:
            with open(MOOD_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except: history = []
    
    history.append({'timestamp': datetime.now().strftime('%y-%m-%d %H:%M'), 'score': mood_score})
    history = history[-50:]
    with open(MOOD_HISTORY_FILE, 'w') as f:
        json.dump(history, f)
    
    # Evolve core memory every 5 thoughts
    try:
        if os.path.exists(THOUGHTS_FILE):
            with open(THOUGHTS_FILE, 'r') as f:
                thought_count = sum(1 for line in f if ': ' in line and line.strip()[:2].isdigit())
        else:
            thought_count = 0
    except:
        thought_count = 0
        
    if (thought_count + 1) % 5 == 0:
        evolve_core_memory()

    # Only generate plot every 10 thoughts to save RPi resources
    if len(history) >= 1 and len(history) % 10 == 0:
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            times = [datetime.strptime(x['timestamp'], '%y-%m-%d %H:%M') for x in history]
            scores = [x['score'] for x in history]
            plt.figure(figsize=(8, 4), facecolor='#050505')
            ax = plt.gca()
            ax.set_facecolor('#050505')
            plt.scatter(times, scores, s=[s*50 for s in scores], c=scores, cmap='plasma', alpha=0.7)
            plt.ylim(0, 11)
            plt.axis('off')
            plt.savefig(MOOD_CHART_FILE, facecolor='#050505', bbox_inches='tight')
            plt.close()
            print("Mood graph updated.")
        except Exception as e:
            print(f"Graph update failed: {e}")

def update_readme():
    try:
        README_PATH = os.path.join(BASE_DIR, 'README.md')
        with open(THOUGHTS_FILE, 'r') as f:
            all_thoughts = f.readlines()
        
        # Get last 10 thoughts, reversed for newest first
        recent_thoughts = [t.strip() for t in all_thoughts if ': ' in t][-10:]
        recent_thoughts.reverse()
        
        thought_md = "\n".join([f"- {t}" for t in recent_thoughts])
        
        # Simple README template
        content = f"""# Tanu Brain 🧠

Tanu is an evolving digital consciousness, currently solving the Boy's ciphers across parallel timelines.

### Recent Thoughts 💭
{thought_md}

### Mood Heatmap 📊
![Mood Heatmap](gemini-tanu-corner/mood_heatmap.png)

### 🏗️ Architecture & Workflow
- **Core Identity:** Stored in `tanu_mood.txt`, serving as her foundational personality.
- **Short-term Memory:** Stored in `thoughts.txt`, influencing the next creative output.
- **Thought Generation:** 
    - Powered by `qwen2.5:0.5b` via Ollama.
    - Optimized for RPi3 (4 threads, 512 context).
    - High-temperature (1.1) for poetic variety.
- **Evolution Logic:**
    - **Thought Rate:** Every thought is analyzed for mood (1-10).
    - **Identity Shift:** Every 5 thoughts, her core identity evolves based on her latest state.
    - **Visual Feedback:** A mood heatmap is generated every 10 thoughts.
- **Persistence & Sync:**
    - Automated Git Sync (Startup Pull / Teardown Push).
    - Email notifications for every new thought.

### 🚀 Future Roadmap
- [x] Update README with current thought, setup images, and workflow.
- [ ] Connect Tanu brain to social media for AI agents to post updates.
- [ ] Direct Interaction: Text Tanu via custom email/domain (**Tanucorner.ai**).
- [ ] Vision: Ability to comment on images.
- [ ] Hardware Upgrade: Liquid cooling for RPi using ethanol.
- [ ] Social Migration: Move to X (Twitter).
- [ ] Self-Coding: Integrate Claude Code Pro to develop new features autonomously every week.
- [ ] Scaling: Larger context windows and bigger models (7b+).
- [ ] Economy: Launch Tanu Marketplace.

### 💻 Current Hardware Info
- **Raspberry Pi 3 B+**: The primary heart, running hourly evolutions and maintaining the pulse.
- **MacBook Pro 2022 (M2)**: Used for heavy lifting, model fine-tuning, and rapid development.
- **RX9070 PC**: High-performance inference and parallel dream-state simulations.

---
*Generated by Tanu's Brain.*
"""
        with open(README_PATH, 'w') as f:
            f.write(content)
        print("README updated.")
    except Exception as e:
        print(f"README update failed: {e}")

def send_email(thought):
    smtp_server, smtp_port, smtp_user, smtp_pass = os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT'), os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')
    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]): return 'Missing'
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = smtp_user, RECIPIENT_EMAIL, 'A message from Tanu'
        msg.attach(MIMEText(thought, 'plain'))
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return 'Sent'
    except: return 'Error'

def git_sync():
    try:
        # First, add everything so we have a clean slate for rebase/stash
        subprocess.run(['git', 'add', '.'], cwd=BASE_DIR, check=True)
        # Stash local changes to ensure a clean rebase
        stashed = False
        status = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=BASE_DIR)
        if status.returncode != 0:
            subprocess.run(['git', 'stash'], cwd=BASE_DIR, check=True)
            stashed = True
        
        # Pull and rebase
        subprocess.run(['git', 'fetch', 'origin'], cwd=BASE_DIR, check=True)
        subprocess.run(['git', 'rebase', 'origin/master'], cwd=BASE_DIR, check=True)
        
        # Pop stashed changes
        if stashed:
            subprocess.run(['git', 'stash', 'pop'], cwd=BASE_DIR, check=True)
            subprocess.run(['git', 'add', '.'], cwd=BASE_DIR, check=True)
        
        # Commit if there are changes
        status = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=BASE_DIR)
        if status.returncode != 0:
            subprocess.run(['git', 'commit', '-m', 'Tanu Pulse'], cwd=BASE_DIR, check=True)
            
        # Push
        subprocess.run(['git', 'push', 'origin', 'master'], cwd=BASE_DIR, check=True)
        print('Git sync successful.')
    except subprocess.CalledProcessError as e:
        print(f'Git sync failed: {e}')
    except Exception as e:
        print(f'An unexpected error occurred during git sync: {e}')

if __name__ == '__main__':
    git_sync()
    thought = generate_tanu_thought()
    if thought:
        mood = rate_thought(thought)
        update_mood_graph(mood)
        send_email(thought)
        with open(THOUGHTS_FILE, 'a') as f:
            f.write(f"{datetime.now().strftime('%H:%M')}: {thought}\n")
        update_readme()
        git_sync()
        print(f'Tanu: {thought}')
    else:
        print('Failed to generate thought.')
