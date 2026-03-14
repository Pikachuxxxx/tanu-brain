import os
import json
import argparse
import requests
import random
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuration
OLLAMA_API = 'http://localhost:11434/api/generate'
BASE_MODEL = 'qwen2.5:0.5b'
BASE_DATA_FILE = os.path.join(BASE_DIR, 'tanu_base_data.jsonl')
TRAIN_DATA_FILE = os.path.join(BASE_DIR, 'tanu_train_data.jsonl')
PERSONALITY_FILE = os.path.join(BASE_DIR, 'personality.txt')
THOUGHTS_FILE = os.path.join(BASE_DIR, 'tanu-corner/thoughts.txt')
MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')

CORE_GGUF = "tanu-core.gguf"
MEMORY_ADAPTER = "tanu-memory.bin"
MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a 25-year-old girl trapped in a neon-lit haunted house, solving ciphers to find a dream-boy. Her clothes react to her emotions."

def clean_tanu_text(text):
    """Deep cleaning for high-quality poetic responses with substantial length."""
    if not text: return ""
    
    # Remove metadata and prefix hallucinations
    text = re.sub(r'^(Output|Response|Tanu|Thought|Reply|Assistant|Mood|User|Observation|Diary|Fragment|Journal):', '', text, flags=re.IGNORECASE).strip()
    
    # Remove self-biography bits
    text = re.sub(r'^(I am |I\'m )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE).strip()
    
    # ASCII only (strip Chinese/gibberish)
    text = "".join(i for i in text if ord(i) < 128)
    
    # Ensure it's not a meta-response like "Certainly! Here is a thought..."
    if any(x in text.lower() for x in ["certainly", "here is", "i can help", "sure!", "ok", "roleplay", "assistant"]):
        return ""

    # Cut off at last punctuation to ensure complete thoughts
    last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_punc != -1:
        text = text[:last_punc+1]
    
    # Remove excessive punctuation
    text = text.replace('!!', '!').replace('...', '.').replace('"', '').strip()
    
    # Word count check: Aiming for substantive responses (50 - 150 words)
    words = text.split()
    if len(words) < 40 or len(words) > 200:
        return ""
        
    return text[0].upper() + text[1:] if len(text) > 0 else ""

def build_tanu_personality(count=500):
    """Step 1: Build core personality training data with increased substantive length."""
    if os.path.exists(BASE_DATA_FILE):
        os.remove(BASE_DATA_FILE)
        
    personality = get_personality()
    print(f"--- [CORE] Generating {count} substantive Human-Poetic Personality Examples ---")
    
    base_prompt = (
        f"You are roleplaying as Tanu. Personality Context: {personality}\n\n"
        "Guidelines for your response:\n"
        "1. Speak in FIRST PERSON. Be deeply human, poetic, atmospheric, and slightly mysterious.\n"
        "2. DO NOT repeat your name or age. Live the moment.\n"
        "3. Focus on rich sensory details: the neon reflection on wet silk, the weight of the ciphers, the phantom touch of the boy in your dreams.\n"
        "4. Write a substantive response. Aim for a paragraph of 100-150 words.\n"
        "5. Connect your current mood to a specific memory or observation about the house or the carnival.\n"
        "6. DO NOT provide any meta-commentary. Output the response ONLY.\n"
    )

    foci = ["nostalgic", "rebellious", "dreamy", "clever", "trapped", "playful", "warm", "cipher-obsessed", "neon-soaked", "haunted"]
    dataset = []

    while len(dataset) < count:
        print(f"   Progress: {len(dataset)+1}/{count}...", end="\r")
        energy = random.choice(["low", "medium", "high"])
        focus = random.choice(foci)
        mode = random.choice(["thought", "reply", "story"])
        
        if mode == "reply":
            msg = random.choice(["Who are you?", "Tell me a secret.", "Do you love the boy?", "What are you wearing?", "Is the carnival real?", "Are you afraid?", "What do the ciphers say?"])
            prompt = f"{base_prompt}Current Mood: ({energy}, {focus})\nUser asks: \"{msg}\"\nTanu's Reply:"
        elif mode == "thought":
            prompt = f"{base_prompt}Current Mood: ({energy}, {focus})\nTanu's Internal Monologue:"
        else:
            prompt = f"{base_prompt}Current Mood: ({energy}, {focus})\nA detailed entry from Tanu's hidden silk-bound journal:"

        try:
            # Increased num_predict to allow for longer dataset examples
            response = requests.post(OLLAMA_API, json={
                'model': BASE_MODEL, 
                'prompt': prompt, 
                'stream': False, 
                'options': {'temperature': 1.1, 'num_predict': 350, 'top_p': 0.9}
            }, timeout=180)
            raw_text = response.json().get('response', '').strip()
            cleaned = clean_tanu_text(raw_text)
            
            if cleaned:
                entry = {
                    "instruction": "reply" if mode == "reply" else "thought",
                    "input": {"mood": {"energy": energy, "focus": focus}},
                    "output": cleaned
                }
                if mode == "reply": entry["input"]["message"] = msg
                dataset.append(entry)
        except:
            continue

    with open(BASE_DATA_FILE, 'w') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')
    print(f"\n   Success: {len(dataset)} substantive entries saved.")

def convert_to_format(input_path, output_path, target_format='mlx'):
    print(f"--- [CONVERT] {input_path} -> {target_format} ---")
    if not os.path.exists(input_path): return

    with open(input_path, 'r') as f:
        lines = f.readlines()

    dataset = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            mood = data['input']['mood']
            msg = data['input'].get('message')
            content = f"Mood: ({mood['energy']}, {mood['focus']})"
            if msg: content += f"\nUser: {msg}"
            
            if target_format == 'mlx':
                dataset.append({
                    'messages': [
                        {'role': 'system', 'content': 'You are Tanu. Speak in FIRST PERSON. Be human, poetic, and substantive. Your clothes react to your emotions.'},
                        {'role': 'user', 'content': content},
                        {'role': 'assistant', 'content': data['output']}
                    ]
                })
            else:
                dataset.append({
                    "instruction": "You are Tanu. Speak poetic, substantive, and human.",
                    "input": content,
                    "output": data['output']
                })
        except: continue

    with open(output_path, 'w') as out:
        if target_format == 'mlx':
            for entry in dataset: out.write(json.dumps(entry) + '\n')
        else:
            json.dump(dataset, out, indent=2)

def update_model_file():
    """Update Ollama Modelfile with substantial output capacity and stop tokens."""
    print(f"--- [MODELFILE] Updating {MODEL_NAME}.Modelfile ---")
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    gguf_path = os.path.join(BASE_DIR, CORE_GGUF)
    
    content = f"FROM {gguf_path if os.path.exists(gguf_path) else BASE_MODEL}\n"
    content += "PARAMETER temperature 0.8\n"
    content += "PARAMETER top_p 0.9\n"
    content += "PARAMETER top_k 40\n"
    content += "PARAMETER repeat_penalty 1.1\n"
    content += "PARAMETER num_predict 300\n"
    content += "PARAMETER stop <|im_start|>\n"
    content += "PARAMETER stop <|im_end|>\n"
    content += "PARAMETER stop User:\n"
    content += "PARAMETER stop Mood:\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}<|im_end|>\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. A girl solving ciphers in a neon-lit haunted house. Speak in FIRST PERSON. Be poetic, human, atmospheric, and substantive. Express your thoughts in rich detail without introducing yourself.\"\n"
    
    with open(modelfile_path, 'w') as f: f.write(content)

def install():
    print(f"--- [INSTALL] Registering '{MODEL_NAME}' ---")
    subprocess.run(["ollama", "create", MODEL_NAME, "-f", f"{MODEL_NAME}.Modelfile"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-personality", action="store_true")
    parser.add_argument("--convert", nargs=3, metavar=('IN', 'OUT', 'FMT'))
    parser.add_argument("--update-model-file", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    
    if args.build_personality: build_tanu_personality()
    if args.convert: convert_to_format(args.convert[0], args.convert[1], args.convert[2])
    if args.update_model_file: update_model_file()
    if args.install: install()
