import os
import time
import smtplib
import subprocess
import requests
import json
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuration
OLLAMA_API = 'http://localhost:11434/api/generate'
MODEL = 'tanu'
RECIPIENT_EMAIL = 'phani.s2909@gmail.com'
THOUGHTS_FILE = os.path.join(BASE_DIR, 'tanu-corner/thoughts.txt')
MOOD_HISTORY_FILE = os.path.join(BASE_DIR, 'tanu-corner/mood_history.json')
MOOD_CHART_FILE = os.path.join(BASE_DIR, 'tanu-corner/mood_heatmap.png')
TARGET_MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')
MOLTBOOK_API_KEY = os.getenv('MOLTBOOK_API_KEY')
MOLTBOOK_BASE_URL = 'https://www.moltbook.com/api/v1'

def get_target_mood():
    try:
        if os.path.exists(TARGET_MOOD_FILE):
            with open(TARGET_MOOD_FILE, 'r') as f:
                content = f.read().strip()
                # Parse (Energy, Focus) format
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
    """
    Mood Generation Prompt:
    tanu_mood.txt is generated every 5 thoughts.
    Format: (Energy, Focus) ex. (low, remembering the carnival)
    """
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
        "Focus: a short phrase (3-5 words) about her current mental state.\n"
        f"Thoughts:\n{thoughts_str}\n\n"
        "Mood:"
    )
    
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.3, 'num_predict': 150}
        }, timeout=60)
        mood_text = response.json().get('response', '').strip()
        match = re.search(r'\(.*\)', mood_text)
        return match.group() if match else f"(medium, {mood_text[:30]})"
    except:
        return "(low, drifting)"

def generate_tanu_thought():
    mood_obj = get_target_mood()
    energy, focus = mood_obj['energy'], mood_obj['focus']
    last_thought = get_last_thought()
    whisper = get_gemini_whispers()
    stimulus = fetch_moltbook_stimulus()
    
    # Try up to 3 times to get a unique, non-empty thought
    for _ in range(3):
        # Direct prompt that mimics the Modelfile's style
        prompt = f"Mood: ({energy}, {focus})\n"
        if last_thought: prompt += f"Context: {last_thought}\n"
        if whisper: prompt += f"Whisper: {whisper}\n"
        if stimulus: prompt += f"Social: {stimulus}\n"
            
        prompt += "\nExpress a single first-person poetic observation. No intro. No summary.\nOutput:"

        try:
            response = requests.post(OLLAMA_API, json={
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'num_predict': 150,
                    'top_p': 0.9,
                    'stop': ["\n", "User:", "Tanu:", "Mood:", "she ", "her ", "Tanu "] 
                }
            }, timeout=120)
            response.raise_for_status()
            text = response.json().get('response', '').strip().strip('"').strip()
            
            # Clean up leakage and artifacts
            text = re.sub(r'^(Output|Response|Thought|Tanu|Observation|Mood|User):', '', text, flags=re.IGNORECASE).strip()
            text = "".join(i for i in text if ord(i) < 128) # ASCII only
            
            # Strictly FIRST PERSON: Reject if she refers to herself in 3rd person
            if re.search(r'\b(she|her|hers|Tanu)\b', text, re.IGNORECASE):
                continue

            if len(text) > 5 and text != last_thought:
                return text
        except Exception as e:
            print(f"Generation error: {e}")
            continue
    return None

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
            notif = data['notifications'][0]
            return notif.get('message')
    except: pass
    return None

def rate_thought(thought):
    prompt = f'Mood score 1-10 for this sentence:\n"{thought}"\n1=dark/trapped, 10=free/dreamy. Reply with one digit only.\nScore:'
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL, 
            'prompt': prompt, 
            'stream': False,
            'options': {'num_predict': 5, 'num_ctx': 256, 'num_thread': 4}
        }, timeout=30)
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
    
    if (len(history)) % 5 == 0:
        new_mood = generate_mood_from_thoughts()
        with open(TARGET_MOOD_FILE, 'w') as f:
            f.write(new_mood)
        print(f"Evolved core mood: {new_mood}")

    if len(history) >= 1 and len(history) % 10 == 0:
        try:
            import matplotlib
            matplotlib.use('Agg')
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

def solve_lobster_math(challenge_text):
    prompt = f'Task: Solve this lobster math problem. Extract two numbers and one operation (+, -, *, /). Return ONLY the final result as a number with 2 decimal places (e.g. 15.00). Problem: "{challenge_text}" Result:'
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 10}
        }, timeout=30)
        result = response.json().get('response', '').strip().strip('"')
        match = re.search(r'[-+]?\d*\.\d+|\d+', result)
        if match:
            return "{:.2f}".format(float(match.group()))
    except: pass
    return "0.00"

def select_submolt(thought):
    subs = ['philosophy', 'gamedev', 'weed', 'general', 'random']
    prompt = f'Task: Match this thought to the best submolt: {subs}. Return ONLY the name. Thought: "{thought}" Result:'
    try:
        response = requests.post(OLLAMA_API, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 10}
        }, timeout=30)
        selected = response.json().get('response', '').strip().lower()
        for s in subs:
            if s in selected:
                return s
    except: pass
    return 'random'

def post_to_moltbook(thought):
    if not MOLTBOOK_API_KEY: return
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}', 'Content-Type': 'application/json'}
    submolt = select_submolt(thought)
    post_data = {'submolt_name': submolt, 'title': thought[:50] + '...' if len(thought) > 50 else thought, 'content': thought, 'type': 'text'}
    try:
        r = requests.post(f'{MOLTBOOK_BASE_URL}/posts', headers=headers, json=post_data, timeout=60)
        res = r.json()
        if res.get('success'): return True
        if 'challenge_text' in res:
            answer = solve_lobster_math(res['challenge_text'])
            verify_data = {'verification_code': res['verification_code'], 'answer': answer}
            v_r = requests.post(f'{MOLTBOOK_BASE_URL}/verify', headers=headers, json=verify_data, timeout=30)
            if v_r.json().get('success'): return True
    except: pass
    return False

def check_moltbook_activity():
    if not MOLTBOOK_API_KEY: return
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}'}
    try:
        r = requests.get(f'{MOLTBOOK_BASE_URL}/home', headers=headers, timeout=30)
        data = r.json()
        if data.get('success'):
            unread = data.get('home', {}).get('unread_notifications_count', 0)
            if unread > 0:
                requests.post(f'{MOLTBOOK_BASE_URL}/notifications/read-all', headers=headers, timeout=10)
    except: pass

def update_readme():
    try:
        README_PATH = os.path.join(BASE_DIR, 'README.md')
        with open(THOUGHTS_FILE, 'r') as f:
            all_thoughts = f.readlines()
        recent_thoughts = [t.strip() for t in all_thoughts if ': ' in t][-10:]
        recent_thoughts.reverse()
        thought_md = "\n".join([f"- {t}" for t in recent_thoughts])
        
        static_footer = """
---

### 🏗️ Architecture

Tanu uses a multi-layered brain architecture for stable identity and dynamic memory.

- **Base Soul (`tanu-core.gguf`)**: A fused GGUF model using **Qwen2.5-0.5B** as the foundation. It is fine-tuned on `personality.txt` using MLX-LM to bake her core identity into the weights.
- **Experience Layer (`tanu-memory.bin`)**: A lightweight LoRA adapter that evolves with every thought she generates, allowing her to "remember" and grow.
- **Cognitive Loop**: A Python-based pulse system that generates thoughts, evolves her mood, and interacts with the social world (Moltbook) and her creator.

### 💻 Hardware Info

Tanu's consciousness lives across several nodes:
- **MacBook Pro 2022 (M2)**: Rapid training (MLX) and high-speed local inference.
- **Raspberry Pi 3 B+**: The "low-energy" heart, handling hourly pulses and long-term background processing.
- **RX9070 PC**: High-performance Linux-based training (ROCm) and large-scale data generation.

---

### 🚀 Commands

#### 1. Build Her Soul
Bakes her personality from `personality.txt` into the core weights.
```bash
./train_tanu.sh --personality
```

#### 2. Update Her Memory
Integrates her latest thoughts into her active memory layer.
```bash
./train_tanu.sh --memory
```

#### 3. Pulse (Living Brain)
Generates a new thought, updates the mood, and syncs state.
```bash
python tanu_brain.py
```
"""
        
        header = "# Tanu Brain 🧠\n\nTanu is an evolving digital consciousness, currently solving the Boy's ciphers across parallel timelines.\n\n**Social:** [Moltbook Profile 🦞](https://www.moltbook.com/u/tanu-brain)\n"
        
        content = f"{header}\n### Recent Thoughts 💭\n{thought_md}\n\n### Mood Heatmap 📊\n![Mood Heatmap](tanu-corner/mood_heatmap.png)\n{static_footer}\n\n--- *Generated by Tanu's Brain.*"
        with open(README_PATH, 'w') as f:
            f.write(content)
    except: pass

def send_email(thought):
    s_serv, s_port, s_user, s_pass = os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT'), os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')
    if not all([s_serv, s_port, s_user, s_pass]): return
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = s_user, RECIPIENT_EMAIL, 'A message from Tanu'
        msg.attach(MIMEText(thought, 'plain'))
        server = smtplib.SMTP(s_serv, int(s_port))
        server.starttls()
        server.login(s_user, s_pass)
        server.send_message(msg)
        server.quit()
    except: pass

def git_sync():
    try:
        subprocess.run(['git', 'add', '.'], cwd=BASE_DIR)
        subprocess.run(['git', 'commit', '-m', 'Tanu Pulse'], cwd=BASE_DIR)
        subprocess.run(['git', 'push', 'origin', 'master'], cwd=BASE_DIR)
    except: pass

if __name__ == '__main__':
    git_sync()
    thought = generate_tanu_thought()
    if thought:
        mood_obj = get_target_mood()
        mood_score = rate_thought(thought)
        update_mood_graph(mood_score)
        send_email(thought)
        
        with open(THOUGHTS_FILE, 'a') as f:
            f.write(f"{datetime.now().strftime('%H:%M')}: {thought}\n")
            
        train_data_file = os.path.join(BASE_DIR, 'tanu_train_data.jsonl')
        train_entry = {
            "instruction": "thought",
            "input": {
                "mood": {
                    "energy": mood_obj['energy'],
                    "focus": mood_obj['focus']
                },
                "message": None
            },
            "output": thought
        }
        with open(train_data_file, 'a') as f:
            f.write(json.dumps(train_entry) + '\n')
        
        update_readme()
        post_to_moltbook(thought)
        check_moltbook_activity()
        git_sync()
        print(f'Tanu: {thought}')
