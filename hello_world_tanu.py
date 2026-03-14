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
    
    # ASCII only
    text = "".join(i for i in text if ord(i) < 128)
    
    # STRICT FIRST PERSON: Reject if she refers to herself in 3rd person
    if re.search(r'\b(she|her|hers|Tanu)\b', text, re.IGNORECASE):
        return ""
        
    # Ensure it's not assistant-speak
    if any(x in text.lower() for x in ["certainly", "here is", "i can help", "sure!", "ok", "roleplay", "assistant"]):
        return ""

    # Cut at last punctuation
    last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_punc != -1: text = text[:last_punc+1]
    
    text = text.replace('!!', '!').replace('...', '.').replace('"', '').strip()
    
    words = text.split()
    if len(words) < 5 or len(words) > 30: # Keep it tight
        return ""
    
    return text[0].upper() + text[1:] if len(text) > 0 else ""

def build_tanu_personality(count=200):
    """Strict first-person generation."""
    print(f"--- [CORE] Strict 1st-Person Generating {count} Samples ---")
    
    if os.path.exists(BASE_DATA_FILE):
        os.remove(BASE_DATA_FILE)
        
    dataset = []
    personality = get_personality()
    
    base_prompt = (
        f"Context: {personality}\n"
        "TASK: Write a short, poetic FIRST PERSON statement ('I', 'my').\n"
        "RULES:\n"
        "1. NEVER use the word 'Tanu' or 'she'.\n"
        "2. Be mysterious and atmospheric.\n"
        "3. Focus on your clothes, the ciphers, or the dream-boy.\n"
        "4. One or two sentences only.\n"
    )

    foci = ["nostalgic", "trapped", "cipher-focused", "neon-soaked", "shadow-fighting"]
    
    generated_count = 0
    with open(BASE_DATA_FILE, 'w') as f:
        while generated_count < count:
            print(f"   Progress: {generated_count}/{count}...", end="\r")
            energy, focus = random.choice(["low", "medium", "high"]), random.choice(foci)
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nOutput:"

            try:
                response = requests.post(OLLAMA_API, json={
                    'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 
                    'options': {'temperature': 1.1, 'num_predict': 100}
                }, timeout=60)
                text = response.json().get('response', '').strip()
                cleaned = clean_tanu_text(text)
                if cleaned:
                    entry = {"instruction": "thought", "input": {"mood": {"energy": energy, "focus": focus}}, "output": cleaned}
                    f.write(json.dumps(entry) + '\n')
                    f.flush()
                    generated_count += 1
            except: continue
            
    print(f"\n   Success: {generated_count} strict entries saved.")


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
    # Use relative path for GGUF
    content = f"FROM ./{CORE_GGUF}\n"
    content += "PARAMETER temperature 0.7\n"
    content += "PARAMETER repeat_penalty 1.3\n"
    content += "PARAMETER num_predict 60\n"
    content += "PARAMETER stop <|im_start|>\n"
    content += "PARAMETER stop <|im_end|>\n"
    content += "PARAMETER stop User:\n"
    content += "PARAMETER stop \". \"\n"
    content += "PARAMETER stop \"\\n\"\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}<|im_end|>\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. Speak ONLY in FIRST PERSON ('I', 'my', 'me'). Example: 'I am a shadow decoding light in the house of silk.' NEVER say 'she', 'Tanu', or 'Ahoy'. NEVER summarize your story. Be poetic and extremely brief (max 10 words). End with a period.\"\n"
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
