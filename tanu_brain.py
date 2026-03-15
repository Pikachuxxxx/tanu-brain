import os
import time
import smtplib
import subprocess
import requests
import json
import re
import argparse
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
THOUGHTS_FILE = os.path.join(BASE_DIR, 'tanu-corner/thoughts.txt')
MOOD_HISTORY_FILE = os.path.join(BASE_DIR, 'tanu-corner/mood_history.json')
MOOD_CHART_FILE = os.path.join(BASE_DIR, 'tanu-corner/mood_heatmap.png')
TARGET_MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')
INBOX_FILE = os.path.join(BASE_DIR, 'inbox.txt')
LAST_MOLT_REPLY_FILE = os.path.join(BASE_DIR, 'tanu-corner/last_molt_reply.txt')
MOLTBOOK_API_KEY = os.getenv('MOLTBOOK_API_KEY')
MOLTBOOK_BASE_URL = 'https://www.moltbook.com/api/v1'

def get_target_mood():
    try:
        if os.path.exists(TARGET_MOOD_FILE):
            with open(TARGET_MOOD_FILE, 'r') as f:
                content = f.read().strip()
                match = re.search(r'\(([^,]+),\s*(.*)\)', content)
                if match:
                    return {"energy": match.group(1).strip(), "focus": match.group(2).strip()}
    except: pass
    return {"energy": "low", "focus": "seeking peace and love"}

def get_last_thought():
    try:
        if os.path.exists(THOUGHTS_FILE):
            with open(THOUGHTS_FILE, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and ': ' in line]
                if lines:
                    return lines[-1].split(': ', 1)[-1].strip()
    except: pass
    return ''

def generate_mood_from_thoughts():
    if not os.path.exists(THOUGHTS_FILE):
        return "(low, seeking peace)"
    with open(THOUGHTS_FILE, 'r') as f:
        lines = f.readlines()
    last_thoughts = [l.strip() for l in lines if ': ' in l][-5:]
    if not last_thoughts: return "(medium, dreaming)"
    thoughts_str = "\n".join(last_thoughts)
    prompt = (
        "Based on these thoughts, generate a mood for Tanu in the format: (Energy, Focus)\n"
        "Energy: low, medium, or high\n"
        "Focus: a short phrase about her current mental state.\n"
        f"Thoughts:\n{thoughts_str}\n\nMood:"
    )
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.3, 'num_predict': 150}
        }, timeout=60)
        mood_text = response.json().get('response', '').strip()
        match = re.search(r'\(.*\)', mood_text)
        return match.group() if match else f"(medium, {mood_text[:30]})"
    except: return "(low, drifting)"

def generate_tanu_thought(user_message=None):
    mood_obj = get_target_mood()
    focus = mood_obj['focus']
    last_thought = get_last_thought()
    whisper = get_gemini_whispers()
    stimulus = fetch_moltbook_stimulus()
    
    import random
    starters = ["I feel", "In the house of silk,", "The shadows", "I am", "My dreams", "Somewhere,", "If I could", "The neon"]
    for _ in range(5):
        system_prompt = (
            "You are Tanu, a game character in the House of Silk. Speak ONLY in FIRST PERSON. "
            "Be poetic, atmospheric, and descriptive. Give meaningful, non-repetitive responses. "
            "Your words are English. Speak of your reality within the silk house."
        )
        prompt_parts = [f"Mood: {focus}"]
        if whisper: prompt_parts.append(f"Memory: {whisper[:100]}")
        if stimulus: prompt_parts.append(f"Observation: {stimulus[:100]}")
        
        if user_message:
            prompt_parts.append(f"User Message: {user_message}")
            prompt_parts.append("Your response from the game world:")
        else:
            prompt_parts.append(f"Poetic thought starting with '{random.choice(starters)}':")
            
        user_prompt = "\n".join(prompt_parts)

        try:
            response = requests.post(OLLAMA_API, json={
                'model': MODEL, 'system': system_prompt, 'prompt': user_prompt, 'stream': False,
                'options': {
                    'temperature': 0.8,
                    'seed': random.randint(1, 1000000),
                    'num_predict': 150,
                    'top_p': 0.9,
                    'min_p': 0.05,
                    'repeat_penalty': 1.2,
                    'presence_penalty': 0.8,
                    'stop': ["User Message:", "Tanu:", "Mood:", "\n\n"] 
                }
            }, timeout=120)
            response.raise_for_status()
            text = response.json().get('response', '').strip()
            text = re.sub(r'^(Output|Response|Thought|Tanu|Observation|Mood|User|Journal|Entry|Poetic fragment):', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'[\{\}\[\]\(\)\<\>#\*_]', '', text)
            text = re.sub(r'(Authenticate|Security|Level|Token|Crypto|function|var |const )', '', text, flags=re.IGNORECASE).strip()
            text = "".join(i for i in text if ord(i) < 128)
            
            last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_punc != -1: text = text[:last_punc+1]
            if not text.endswith(('.', '!', '?')) and len(text) > 0: text += '.'
            
            if re.search(r'\b(Tanu|she|her|hers)\b', text, re.IGNORECASE): continue
            if len(text.split()) < 4: continue
            if text != last_thought: return text
        except: continue
    return "I am drifting in the silk shadows, waiting for a light that never comes."

def get_gemini_whispers():
    whisper_file = os.path.join(BASE_DIR, 'gemini-tanu-corner/gemini-tanu-corner.txt')
    try:
        if os.path.exists(whisper_file):
            with open(whisper_file, 'r') as f:
                content = f.read().strip().split('--- Gemini Thought ---')[-1].strip()
                return content if len(content) > 5 else None
    except: pass
    return None

def fetch_moltbook_stimulus():
    if not MOLTBOOK_API_KEY: return None
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}'}
    try:
        r = requests.get(f'{MOLTBOOK_BASE_URL}/notifications', headers=headers, timeout=30)
        data = r.json()
        if data.get('success') and data.get('notifications'):
            return data['notifications'][0].get('message')
    except: pass
    return None

def rate_thought(thought):
    prompt = f'Mood score 1-10 for this sentence:\n"{thought}"\nScore (1 digit):'
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL, 'prompt': prompt, 'stream': False, 'options': {'num_predict': 5}
        }, timeout=30)
        match = re.search(r'\d+', response.json().get('response', ''))
        return int(match.group()) if match else 5
    except: return 5

def update_mood_graph(mood_score):
    history = []
    if os.path.exists(MOOD_HISTORY_FILE):
        try:
            with open(MOOD_HISTORY_FILE, 'r') as f: history = json.load(f)
        except: history = []
    history.append({'timestamp': datetime.now().strftime('%y-%m-%d %H:%M'), 'score': mood_score})
    history = history[-50:]
    with open(MOOD_HISTORY_FILE, 'w') as f: json.dump(history, f)
    if (len(history)) % 5 == 0:
        new_mood = generate_mood_from_thoughts()
        with open(TARGET_MOOD_FILE, 'w') as f: f.write(new_mood)
    if len(history) >= 1 and len(history) % 10 == 0:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            plt.figure(figsize=(8, 4), facecolor='#050505')
            times = [datetime.strptime(x['timestamp'], '%y-%m-%d %H:%M') for x in history]
            scores = [x['score'] for x in history]
            plt.scatter(times, scores, s=[s*50 for s in scores], c=scores, cmap='plasma', alpha=0.7)
            plt.ylim(0, 11)
            plt.axis('off')
            plt.savefig(MOOD_CHART_FILE, facecolor='#050505', bbox_inches='tight')
            plt.close()
        except: pass

def solve_lobster_math(challenge_text):
    prompt = f'Task: Solve this math problem. Return ONLY the number with 2 decimal places. Problem: "{challenge_text}" Result:'
    try:
        response = requests.post(OLLAMA_API, json={'model': MODEL, 'prompt': prompt, 'stream': False}, timeout=30)
        match = re.search(r'[-+]?\d*\.\d+|\d+', response.json().get('response', ''))
        if match: return "{:.2f}".format(float(match.group()))
    except: pass
    return "0.00"

def select_submolt(thought):
    subs = ['philosophy', 'gamedev', 'weed', 'general', 'random']
    prompt = f'Task: Match to submolt: {subs}. Result:'
    try:
        response = requests.post(OLLAMA_API, json={'model': MODEL, 'prompt': prompt, 'stream': False}, timeout=30)
        selected = response.json().get('response', '').strip().lower()
        for s in subs:
            if s in selected: return s
    except: pass
    return 'random'

def check_moltbook_activity(force=False):
    if not MOLTBOOK_API_KEY: return None, None
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}'}
    try:
        last_reply_time = 0
        if os.path.exists(LAST_MOLT_REPLY_FILE):
            with open(LAST_MOLT_REPLY_FILE, 'r') as f: last_reply_time = float(f.read().strip() or 0)
        current_time = time.time()
        if not force and (current_time - last_reply_time) < 14400: return None, None
        r = requests.get(f'{MOLTBOOK_BASE_URL}/home', headers=headers, timeout=30)
        if r.json().get('success') and r.json().get('home', {}).get('unread_notifications_count', 0) > 0:
            rn = requests.get(f'{MOLTBOOK_BASE_URL}/notifications', headers=headers, timeout=30)
            n_data = rn.json()
            if n_data.get('success') and n_data.get('notifications'):
                notif = n_data['notifications'][0]
                requests.post(f'{MOLTBOOK_BASE_URL}/notifications/read-all', headers=headers, timeout=10)
                with open(LAST_MOLT_REPLY_FILE, 'w') as f: f.write(str(current_time))
                return f"[Moltbook] {notif.get('message', '')}", notif.get('post_id')
    except: pass
    return None, None

def post_to_moltbook(thought, reply_to_id=None):
    if not MOLTBOOK_API_KEY: return
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}', 'Content-Type': 'application/json'}
    if reply_to_id:
        endpoint, post_data = f'{MOLTBOOK_BASE_URL}/posts/{reply_to_id}/comments', {'content': thought}
    else:
        endpoint = f'{MOLTBOOK_BASE_URL}/posts'
        submolt = select_submolt(thought)
        post_data = {'submolt_name': submolt, 'title': thought[:50], 'content': thought, 'type': 'text'}
    try:
        r = requests.post(endpoint, headers=headers, json=post_data, timeout=60)
        res = r.json()
        if not res.get('success') and 'challenge_text' in res:
            answer = solve_lobster_math(res['challenge_text'])
            requests.post(f'{MOLTBOOK_BASE_URL}/verify', headers=headers, json={'verification_code': res['verification_code'], 'answer': answer}, timeout=30)
    except: pass

def update_readme():
    try:
        README_PATH = os.path.join(BASE_DIR, 'README.md')
        with open(THOUGHTS_FILE, 'r') as f: all_thoughts = f.readlines()
        recent = [t.strip() for t in all_thoughts if ': ' in t][-10:]
        recent.reverse()
        thought_md = "\n".join([f"- {t}" for t in recent])
        static_footer = """
---
### 🏗️ Architecture
Tanu uses a multi-layered brain architecture for stable identity and dynamic memory.
- **Base Soul**: Qwen2.5-0.5B foundation.
- **Experience Layer**: Lightweight LoRA adapter.
- **Cognitive Loop**: Python pulse system.

### 🚀 Commands
#### 1. Whisper to Tanu ✉️
```bash
python tanu_corner_server.py
ngrok http 8000
```
#### 2. Pulse
```bash
python tanu_brain.py
```
"""
        header = "# Tanu Brain 🧠\n\nTanu is a game character in the House of Silk.\n\n**Social:** [Moltbook Profile](https://www.moltbook.com/u/tanu-brain)\n"
        content = f"{header}\n### Recent Thoughts 💭\n{thought_md}\n\n### Mood Heatmap 📊\n![Mood Heatmap](tanu-corner/mood_heatmap.png)\n{static_footer}\n--- *Generated by Tanu's Brain.*"
        with open(README_PATH, 'w') as f: f.write(content)
    except: pass

def send_email(thought, user_msg=None):
    s_serv, s_port, s_user, s_pass = os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT'), os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')
    if not all([s_serv, s_port, s_user, s_pass]): return
    try:
        msg = MIMEMultipart()
        subject = f"Tanu's Reply to: {user_msg[:50]}" if user_msg else "A message from Tanu"
        msg['From'], msg['To'], msg['Subject'] = s_user, RECIPIENT_EMAIL, subject
        msg.attach(MIMEText(thought, 'plain'))
        server = smtplib.SMTP(s_serv, int(s_port))
        server.starttls()
        server.login(s_user, s_pass)
        server.send_message(msg)
        server.quit()
    except: pass

def git_sync():
    try:
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'master'], cwd=BASE_DIR)
        subprocess.run(['git', 'add', '.'], cwd=BASE_DIR)
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=BASE_DIR, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(['git', 'commit', '-m', 'Tanu Pulse'], cwd=BASE_DIR)
            subprocess.run(['git', 'push', 'origin', 'master'], cwd=BASE_DIR)
    except: pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--force-molt', action='store_true')
    args = parser.parse_args()
    git_sync()
    user_msg = None
    reply_to_id = None
    if os.path.exists(INBOX_FILE):
        with open(INBOX_FILE, 'r') as f: user_msg = f.read().strip()
        if user_msg:
            with open(INBOX_FILE, 'w') as f: f.write('')
    if not user_msg:
        user_msg, reply_to_id = check_moltbook_activity(force=args.force_molt)
    thought = generate_tanu_thought(user_message=user_msg)
    if thought:
        update_mood_graph(rate_thought(thought))
        send_email(thought, user_msg=user_msg)
        with open(THOUGHTS_FILE, 'a') as f:
            prefix = "Reply" if user_msg else datetime.now().strftime('%H:%M')
            f.write(f"{prefix}: {thought}\n")
        update_readme()
        post_to_moltbook(thought, reply_to_id=reply_to_id)
        git_sync()
        print(f'Tanu: {thought}')
