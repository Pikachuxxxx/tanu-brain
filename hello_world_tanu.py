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
    text = re.sub(r'^(Output|Response|Tanu|Thought|Reply|Assistant|Mood|User|Observation|Diary|Fragment|Journal|Internal Monologue):', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(I am |I\'m )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE).strip()
    text = "".join(i for i in text if ord(i) < 128) # ASCII
    
    # Ensure it's not assistant-speak
    if any(x in text.lower() for x in ["certainly", "here is", "i can help", "sure!", "ok", "roleplay", "assistant"]):
        return ""

    # Cut at last punctuation
    last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_punc != -1: text = text[:last_punc+1]
    
    text = text.replace('!!', '!').replace('...', '.').replace('"', '').strip()
    
    # Check length (80-150 words for substantive training)
    words = text.split()
    if len(words) < 60:
        return ""
    
    return text[0].upper() + text[1:] if len(text) > 0 else ""

def build_tanu_personality(count=100):
    """Clean substantive generation to flush out poisoned weights."""
    print(f"--- [CORE] Substantive Generating {count} Clean Samples ---")
    
    if os.path.exists(BASE_DATA_FILE):
        os.remove(BASE_DATA_FILE)
        
    personality = get_personality()
    base_prompt = (
        f"Roleplay as Tanu. Context: {personality}\n"
        "Rules:\n"
        "1. Speak in FIRST PERSON. Be deeply poetic and atmospheric.\n"
        "2. Focus on: ciphers, the neon, the boy, or the house.\n"
        "3. Length: Write 100-150 words.\n"
        "4. NO meta-talk, NO 'answer', NO 'ylation'. Respond directly.\n"
    )

    foci = ["nostalgic", "rebellious", "dreamy", "trapped", "cipher-focused", "neon-soaked"]
    
    generated_count = 0
    with open(BASE_DATA_FILE, 'w') as f:
        while generated_count < count:
            print(f"   Progress: {generated_count}/{count}...", end="\r")
            energy, focus = random.choice(["low", "medium", "high"]), random.choice(foci)
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nOutput:"

            try:
                response = requests.post(OLLAMA_API, json={
                    'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 
                    'options': {'temperature': 1.1, 'num_predict': 400}
                }, timeout=180)
                text = response.json().get('response', '').strip()
                cleaned = clean_tanu_text(text)
                if cleaned:
                    entry = {"instruction": "thought", "input": {"mood": {"energy": energy, "focus": focus}}, "output": cleaned}
                    f.write(json.dumps(entry) + '\n')
                    f.flush()
                    generated_count += 1
            except: continue
            
    print(f"\n   Success: {generated_count} clean substantive entries saved.")

def convert_to_format(input_path, output_path, target_format='mlx'):
    if not os.path.exists(input_path): return
    with open(input_path, 'r') as f: lines = f.readlines()
    dataset = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            mood = data['input']['mood']
            content = f"Mood: ({mood['energy']}, {mood['focus']})"
            if target_format == 'mlx':
                dataset.append({'messages': [{'role': 'system', 'content': 'You are Tanu. Speak in FIRST PERSON. Be poetic and substantive.'}, {'role': 'user', 'content': content}, {'role': 'assistant', 'content': data['output']}]})
            else:
                dataset.append({"instruction": "You are Tanu.", "input": content, "output": data['output']})
        except: continue
    with open(output_path, 'w') as out:
        if target_format == 'mlx':
            for entry in dataset: out.write(json.dumps(entry) + '\n')
        else: json.dump(dataset, out, indent=2)

def update_model_file():
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    content = f"FROM ./{CORE_GGUF}\n"
    content += "PARAMETER temperature 0.3\n"
    content += "PARAMETER top_p 0.5\n"
    content += "PARAMETER repeat_penalty 1.5\n"
    content += "PARAMETER num_predict 150\n"
    content += "PARAMETER stop <|im_start|>\n"
    content += "PARAMETER stop <|im_end|>\n"
    content += "PARAMETER stop User:\n"
    content += "PARAMETER stop \"answer\"\n"
    content += "PARAMETER stop \"ylation\"\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. Speak in FIRST PERSON. Be poetic, human, and substantive. NEVER use third person or your name. End with a period.\"\n"
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
