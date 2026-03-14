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
PERSONALITY_FILE = os.path.join(BASE_DIR, 'personality.txt')

CORE_GGUF = "tanu-core.gguf"
MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a 25-year-old girl trapped in a neon-lit haunted house, solving ciphers to find a dream-boy."

def clean_tanu_text(text):
    if not text: return ""
    # Strip meta labels and bio-garbage
    text = re.sub(r'^(Output|Response|Tanu|Thought|Reply|Assistant|Mood|User|Observation|Diary|Fragment|Journal):', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(I am |I\'m )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE).strip()
    text = "".join(i for i in text if ord(i) < 128) # ASCII
    
    # Ensure it's not assistant-speak
    if any(x in text.lower() for x in ["certainly", "here is", "i can help", "sure!", "ok", "roleplay", "assistant", "certainly!"]):
        return ""

    # Cut at last punctuation
    last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_punc != -1: text = text[:last_punc+1]
    
    text = text.replace('!!', '!').replace('...', '.').replace('"', '').strip()
    
    # Check length (100-150 words as requested)
    words = text.split()
    if len(words) < 80: # Allow some buffer below 100
        return ""
    
    return text[0].upper() + text[1:] if len(text) > 0 else ""

def build_tanu_personality(count=100):
    """Quick high-quality generation with hardcoded anchors and substantial length."""
    print(f"--- [CORE] Substantive Generating {count} Samples ---")
    
    dataset = []
    personality = get_personality()
    
    base_prompt = (
        f"Roleplay as Tanu. Context: {personality}\n"
        "Guidelines:\n"
        "1. Speak in FIRST PERSON. Be deeply poetic, atmospheric, and mysterious.\n"
        "2. Focus on: ciphers, the humming neon, the boy in your dreams, or the house's secrets.\n"
        "3. Length: Write a substantial paragraph (100-150 words).\n"
        "4. NO name/age summaries. Respond directly as the character.\n"
    )

    foci = ["nostalgic", "rebellious", "dreamy", "trapped", "cipher-focused", "neon-soaked", "shadow-fighting"]
    
    while len(dataset) < count:
        print(f"   Progress: {len(dataset)}/{count}...", end="\r")
        energy, focus = random.choice(["low", "medium", "high"]), random.choice(foci)
        mode = random.choice(["thought", "reply", "journal"])
        
        if mode == "reply":
            msg = random.choice(["Who are you?", "What do you see?", "Is it a dream?", "Tell me a secret."])
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nUser asks: \"{msg}\"\nTanu's Reply:"
        elif mode == "thought":
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nInternal Monologue:"
        else:
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nA hidden diary entry:"

        try:
            # Use high num_predict for long responses
            response = requests.post(OLLAMA_API, json={
                'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 
                'options': {'temperature': 1.1, 'num_predict': 350, 'top_p': 0.9}
            }, timeout=180)
            text = response.json().get('response', '').strip()
            cleaned = clean_tanu_text(text)
            if cleaned:
                entry = {"instruction": mode, "input": {"mood": {"energy": energy, "focus": focus}}, "output": cleaned}
                if mode == "reply": entry["input"]["message"] = msg
                dataset.append(entry)
        except: continue

    with open(BASE_DATA_FILE, 'w') as f:
        for entry in dataset: f.write(json.dumps(entry) + '\n')
    print(f"\n   Success: {len(dataset)} substantive entries saved.")

def convert_to_format(input_path, output_path, target_format='mlx'):
    if not os.path.exists(input_path): return
    with open(input_path, 'r') as f: lines = f.readlines()
    dataset = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            mood, msg = data['input']['mood'], data['input'].get('message')
            content = f"Mood: ({mood['energy']}, {mood['focus']})"
            if msg: content += f"\nUser: {msg}"
            if target_format == 'mlx':
                dataset.append({'messages': [{'role': 'system', 'content': 'You are Tanu. Speak in FIRST PERSON. Be poetic, human, and substantive.'}, {'role': 'user', 'content': content}, {'role': 'assistant', 'content': data['output']}]})
            else:
                dataset.append({"instruction": "You are Tanu.", "input": content, "output": data['output']})
        except: continue
    with open(output_path, 'w') as out:
        if target_format == 'mlx':
            for entry in dataset: out.write(json.dumps(entry) + '\n')
        else: json.dump(dataset, out, indent=2)

def update_model_file():
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    gguf_path = os.path.join(BASE_DIR, CORE_GGUF)
    content = f"FROM {gguf_path if os.path.exists(gguf_path) else BASE_MODEL}\n"
    content += "PARAMETER temperature 0.8\nPARAMETER repeat_penalty 1.2\nPARAMETER num_predict 350\n"
    content += "PARAMETER stop <|im_start|>\nPARAMETER stop <|im_end|>\nPARAMETER stop User:\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}<|im_end|>\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. A girl solving ciphers in a neon-lit haunted house. Speak in FIRST PERSON. Be poetic, human, and substantive. Express your thoughts in rich, long detail.\"\n"
    with open(modelfile_path, 'w') as f: f.write(content)

def install():
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
