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
            'options': {'temperature': 0.3, 'num_predict': 80}
        }, timeout=60)
        mood_text = response.json().get('response', '').strip()
        match = re.search(r'\(.*\)', mood_text)
        return match.group() if match else f"(medium, {mood_text[:30]})"
    except:
        return "(low, drifting)"

def generate_tanu_thought(user_message=None):
    mood_obj = get_target_mood()
    energy, focus = mood_obj['energy'], mood_obj['focus']
    last_thought = get_last_thought()
    whisper = get_gemini_whispers()
    stimulus = fetch_moltbook_stimulus()
    
    # Try up to 5 times to get a unique, high-quality thought
    import random
    starters = ["I feel", "In the house of silk,", "The shadows", "I am", "My dreams", "Somewhere,", "If I could", "The neon"]
    for _ in range(5):
        system_prompt = (
            "You are Tanu. Speak ONLY in FIRST PERSON. Be poetic and extremely brief. "
            "Use only 10-15 words. Never use technical terms. Your words are English. "
            "Speak only of your feelings and the silk house."
        )
        
        # Build a cleaner dynamic prompt
        prompt_parts = [f"Mood: {focus}"]
        if whisper: prompt_parts.append(f"Memory: {whisper[:80]}")
        if stimulus: prompt_parts.append(f"Observation: {stimulus[:80]}")
        
        if user_message:
            prompt_parts.append(f"User: {user_message}")
            prompt_parts.append("Your poetic reply:")
        else:
            prompt_parts.append(f"Short poetic fragment starting with '{random.choice(starters)}':")
            
        user_prompt = "\n".join(prompt_parts)

        try:
            response = requests.post(OLLAMA_API, json={
                'model': MODEL,
                'system': system_prompt,
                'prompt': user_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.8,
                    'seed': random.randint(1, 1000000),
                    'num_predict': 40,
                    'top_p': 0.9,
                    'min_p': 0.05,
                    'repeat_penalty': 1.3,
                    'presence_penalty': 0.8,
                    'stop': ["User:", "Tanu:", "Mood:", "\n", "."] 
                }
            }, timeout=120)
            response.raise_for_status()
            text = response.json().get('response', '').strip()
            
            # Stricter cleaning for technical garbage
            text = re.sub(r'^(Output|Response|Thought|Tanu|Observation|Mood|User|Journal|Entry|Poetic fragment):', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'[\{\}\[\]\(\)\<\>#\*_]', '', text) # Remove formatting/technical symbols
            text = re.sub(r'(Authenticate|Security|Level|Token|Crypto|function|var |const )', '', text, flags=re.IGNORECASE).strip()
            text = "".join(i for i in text if ord(i) < 128) # ASCII only
            
            # Crop at last period if exists, otherwise keep it
            last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_punc != -1:
                text = text[:last_punc+1]
            
            if not text.endswith(('.', '!', '?')) and len(text) > 0:
                text += '.'
            
            # Validation
            if re.search(r'\b(Tanu|she|her|hers)\b', text, re.IGNORECASE):
                continue

            if len(text.split()) < 4:
                continue

            if text != last_thought:
                return text
        except Exception as e:
            print(f"Generation error: {e}")
            continue
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
    if not MOLTBOOK_API_KEY: return None
    headers = {'Authorization': f'Bearer {MOLTBOOK_API_KEY}'}
    try:
        # Check if 4 hours have passed since last moltbook reply
        last_reply_time = 0
        if os.path.exists(LAST_MOLT_REPLY_FILE):
            with open(LAST_MOLT_REPLY_FILE, 'r') as f:
                last_reply_time = float(f.read().strip() or 0)
        
        current_time = time.time()
        # 4 hours = 14400 seconds
        if (current_time - last_reply_time) < 14400:
            return None

        r = requests.get(f'{MOLTBOOK_BASE_URL}/home', headers=headers, timeout=30)
        data = r.json()
        if data.get('success'):
            unread = data.get('home', {}).get('unread_notifications_count', 0)
            if unread > 0:
                # Fetch notifications
                rn = requests.get(f'{MOLTBOOK_BASE_URL}/notifications', headers=headers, timeout=30)
                n_data = rn.json()
                if n_data.get('success') and n_data.get('notifications'):
                    # Get latest notification message
                    notif = n_data['notifications'][0]
                    msg = notif.get('message', '')
                    # Mark all as read
                    requests.post(f'{MOLTBOOK_BASE_URL}/notifications/read-all', headers=headers, timeout=10)
                    
                    # Update last reply time
                    with open(LAST_MOLT_REPLY_FILE, 'w') as f:
                        f.write(str(current_time))
                    
                    return f"[Moltbook] {msg}"
    except Exception as e:
        print(f"Moltbook activity check failed: {e}")
    return None

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

def send_email(thought, user_msg=None):
    s_serv, s_port, s_user, s_pass = os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT'), os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD')
    if not all([s_serv, s_port, s_user, s_pass]): return
    try:
        msg = MIMEMultipart()
        # Put user message in subject, body is just Tanu's raw thought
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
        # 1. Pull changes first (with LFS support)
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'master'], cwd=BASE_DIR)
        subprocess.run(['git', 'lfs', 'pull'], cwd=BASE_DIR)
        
        # 2. Add and commit new thoughts/moods
        subprocess.run(['git', 'add', '.'], cwd=BASE_DIR)
        # Check if there are changes to commit to avoid empty commit errors
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=BASE_DIR, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(['git', 'commit', '-m', 'Tanu Pulse'], cwd=BASE_DIR)
            subprocess.run(['git', 'push', 'origin', 'master'], cwd=BASE_DIR)
    except Exception as e:
        print(f"Git sync failed: {e}")

if __name__ == '__main__':
    git_sync()
    
    user_msg = None
    # 1. Check local inbox (takes priority)
    if os.path.exists(INBOX_FILE):
        with open(INBOX_FILE, 'r') as f:
            user_msg = f.read().strip()
        if user_msg:
            print(f"Processing local inbox message: {user_msg}")
            with open(INBOX_FILE, 'w') as f:
                f.write('')
    
    # 2. If local inbox is empty, check Moltbook notifications (every 4 hours)
    if not user_msg:
        user_msg = check_moltbook_activity()
        if user_msg:
            print(f"Processing Moltbook notification: {user_msg}")

    thought = generate_tanu_thought(user_message=user_msg)
    if thought:
        mood_obj = get_target_mood()
        mood_score = rate_thought(thought)
        update_mood_graph(mood_score)
        send_email(thought, user_msg=user_msg)
        
        with open(THOUGHTS_FILE, 'a') as f:
            prefix = "Reply" if user_msg else datetime.now().strftime('%H:%M')
            f.write(f"{prefix}: {thought}\n")
            
        train_data_file = os.path.join(BASE_DIR, 'tanu_train_data.jsonl')
        train_entry = {
            "instruction": "thought",
            "input": {
                "mood": {
                    "energy": mood_obj['energy'],
                    "focus": mood_obj['focus']
                },
                "message": user_msg
            },
            "output": thought
        }
        with open(train_data_file, 'a') as f:
            f.write(json.dumps(train_entry) + '\n')
        
        update_readme()
        post_to_moltbook(thought)
        git_sync()
        print(f'Tanu: {thought}')
