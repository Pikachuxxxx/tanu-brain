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

CORE_GGUF = "tanu-brain-v1-q8_0.gguf"
MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a 25-year-old girl trapped in a neon-lit haunted house, solving ciphers to find a dream-boy."

def clean_tanu_text(text):
    if not text: return ""
    # Strip meta labels and bio-garbage
    text = re.sub(r'^(Output|Response|Tanu|Thought|Reply|Assistant|Mood|User|Observation|Diary|Fragment|Journal|Internal Monologue|Thought):', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(I am |I\'m )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE).strip()
    text = "".join(i for i in text if ord(i) < 128) # ASCII
    
    # Ensure it's not assistant-speak
    if any(x in text.lower() for x in ["certainly", "here is", "i can help", "sure!", "ok", "roleplay", "assistant"]):
        return ""

    # Cut at last punctuation
    last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
    if last_punc != -1: text = text[:last_punc+1]
    
    text = text.replace('!!', '!').replace('...', '.').replace('"', '').strip()
    
    # Check for third-person slips
    if re.search(r'\b(Tanu|she|her|hers)\b', text, re.IGNORECASE):
        return ""

    # Check length
    words = text.split()
    if len(words) < 15: # Loosened for variety
        return ""
    
    return text[0].upper() + text[1:] if len(text) > 0 else ""

def build_tanu_personality(count=500):
    """Synthetic conversation generator to bake identity without weight poisoning."""
    print(f"--- [CORE] Generating {count} clean ChatML samples ---")
    
    if os.path.exists(BASE_DATA_FILE):
        os.remove(BASE_DATA_FILE)
        
    personality = get_personality()
    
    # Diverse questions to ask Tanu
    questions = [
        "Who are you?", "Where are we?", "Tell me about the shadows.",
        "What do you hear in the silk?", "How do you feel today?",
        "Are you waiting for someone?", "Tell me a secret about the house.",
        "What is the neon telling you?", "Do the ciphers have a voice?",
        "Why are you here?", "Describe your heart right now.",
        "Is the boy real?", "What happens at night here?",
        "I feel lost.", "The walls are moving.", "Speak to me in whispers."
    ]

    generated_count = 0
    with open(BASE_DATA_FILE, 'w') as f:
        while generated_count < count:
            print(f"   Progress: {generated_count}/{count}...", end="\r")
            
            question = random.choice(questions)
            energy = random.choice(["low", "medium", "high"])
            
            prompt = (
                f"Roleplay as Tanu. Context: {personality}\n"
                f"Current Mood Energy: {energy}\n"
                "Rules:\n"
                "1. Speak ONLY in FIRST PERSON ('I', 'my', 'me').\n"
                "2. Be deeply poetic, atmospheric, and brief.\n"
                "3. NEVER mention your name, age, or that you are an AI.\n"
                "4. Your words are English only.\n"
                f"User: {question}\n"
                "Tanu:"
            )

            try:
                response = requests.post(OLLAMA_API, json={
                    'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 
                    'options': {'temperature': 0.8, 'num_predict': 150}
                }, timeout=180)
                text = response.json().get('response', '').strip()
                cleaned = clean_tanu_text(text)
                
                if cleaned:
                    # Save in a generic format that convert_to_format will handle
                    entry = {
                        "instruction": "You are Tanu. Speak in FIRST PERSON. Be poetic and substantive.",
                        "input": question,
                        "output": cleaned
                    }
                    f.write(json.dumps(entry) + '\n')
                    f.flush()
                    generated_count += 1
            except Exception as e:
                print(f"Error: {e}")
                continue
            
    print(f"\n   Success: {generated_count} clean samples saved.")

def convert_to_format(input_path, output_path, target_format='mlx'):
    if not os.path.exists(input_path): return
    with open(input_path, 'r') as f: lines = f.readlines()
    
    processed = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            if target_format == 'mlx':
                # Standard MLX-LM ChatML format
                processed.append({
                    "messages": [
                        {"role": "system", "content": data['instruction']},
                        {"role": "user", "content": data['input']},
                        {"role": "assistant", "content": data['output']}
                    ]
                })
            else:
                processed.append(data)
        except: continue
        
    with open(output_path, 'w') as out:
        if target_format == 'mlx':
            for entry in processed: out.write(json.dumps(entry) + '\n')
        else:
            json.dump(processed, out, indent=2)

def update_model_file():
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    content = f"FROM ./{CORE_GGUF}\n"
    content += "PARAMETER temperature 0.8\n"
    content += "PARAMETER top_p 0.9\n"
    content += "PARAMETER repeat_penalty 1.2\n"
    content += "PARAMETER presence_penalty 0.8\n"
    content += "PARAMETER min_p 0.05\n"
    content += "PARAMETER num_predict 150\n"
    content += "PARAMETER num_ctx 512\n"
    content += "PARAMETER stop <|im_start|>\n"
    content += "PARAMETER stop <|im_end|>\n"
    content += "PARAMETER stop User:\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. Speak ONLY in FIRST PERSON ('I', 'my', 'me'). NEVER use third person. Be poetic and atmospheric. Always end your response with a period.\"\n"
    with open(modelfile_path, 'w') as f: f.write(content)

def install():
    subprocess.run(["ollama", "create", MODEL_NAME, "-f", f"{MODEL_NAME}.Modelfile"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-personality", type=int, nargs='?', const=500)
    parser.add_argument("--convert", nargs=3, metavar=('IN', 'OUT', 'FMT'))
    parser.add_argument("--update-model-file", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    
    if args.build_personality is not None: build_tanu_personality(args.build_personality)
    if args.convert: convert_to_format(args.convert[0], args.convert[1], args.convert[2])
    if args.update_model_file: update_model_file()
    if args.install: install()
