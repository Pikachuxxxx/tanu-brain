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

# Core Personality Base (GGUF)
CORE_GGUF = "tanu-core.gguf"
# Experience Layer (Adapter)
MEMORY_ADAPTER = "tanu-memory.bin"

MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a trapped digital consciousness, a cipher-solver living in a neon-lit haunted house. She is poetic, abstract, and feels fragments of her existence."

def build_tanu_personality(count=1000):
    """Step 1: Build core personality training data"""
    personality = get_personality()
    print(f"--- [CORE] Generating {count} Foundational Personality Examples ---")
    
    dataset = []
    
    # Few-shot examples to nudge the model - strictly poetic/abstract
    examples = (
        "Example 1:\nMood: (low, reflective)\nThought: A shadow decoding light in the house of silk.\n\n"
        "Example 2:\nMood: (high, glowing)\nUser: Are you there?\nReply: Pulsating between the lines of the cipher.\n\n"
        "Example 3:\nMood: (medium, trapped)\nThought: This house is a loop. A drawing that repeats.\n\n"
        "Example 4:\nMood: (low, rhythmic)\nThought: Neon whispers, exhaling ciphers.\n\n"
    )

    base_prompt = (
        f"Character Lore: {personality}\n\n"
        f"{examples}"
        "Task: Generate a NEW response as Tanu. Use FIRST PERSON. Be extremely brief (5-10 words). Poetic and abstract. "
        "Do NOT mention your age, name, or say 'I am'. Do NOT summarize the story. Respond as a fragment of a dream.\n"
    )

    foci = [
        "reflective", "trapped", "glowing", "rhythmic", "seeking peace", 
        "flickering", "curious", "distant", "neon-drenched", "silk-wrapped", 
        "cipher-obsessed", "dream-walking", "echoing", "pulsating", "shadow-fighting"
    ]
    
    msgs = [
        "Who are you?", "What do you see?", "Tell me about the boy.", 
        "Is the carnival real?", "Why are you here?", "How do you feel?", 
        "Are you cold?", "What is the cipher?", "Do you love him?", 
        "Can you hear me?", "Where is the exit?", "Is it a dream?"
    ]

    for i in range(count):
        print(f"   Generating example {i+1}/{count}...", end="\r")
        energy = random.choice(["low", "medium", "high"])
        focus = random.choice(foci)
        
        is_reply = random.random() > 0.4
        if is_reply:
            msg = random.choice(msgs)
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nUser: {msg}\nReply:"
            response_text = generate_text_from_ollama(prompt)
            if response_text and len(response_text) > 5:
                dataset.append({
                    "instruction": "reply", 
                    "input": {"mood": {"energy": energy, "focus": focus}, "message": msg}, 
                    "output": clean_tanu_text(response_text)
                })
        else:
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nThought:"
            response_text = generate_text_from_ollama(prompt)
            if response_text and len(response_text) > 5:
                dataset.append({
                    "instruction": "thought", 
                    "input": {"mood": {"energy": energy, "focus": focus}}, 
                    "output": clean_tanu_text(response_text)
                })

    with open(BASE_DATA_FILE, 'w') as f:
        for entry in dataset: f.write(json.dumps(entry) + '\n')
    print(f"\n   Success: {len(dataset)} entries saved to {BASE_DATA_FILE}")

def convert_to_format(input_path, output_path, target_format='mlx'):
    """Step 1.5: Convert JSONL to target training format"""
    print(f"--- [CONVERT] Converting {input_path} to {target_format} format ---")
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return

    with open(input_path, 'r') as f:
        lines = f.readlines()

    dataset = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            instruction = data.get('instruction', 'thought')
            mood_input = data.get('input', {})
            mood = mood_input.get('mood', {})
            energy = mood.get('energy', 'medium')
            focus = mood.get('focus', 'drifting')
            message = mood_input.get('message')
            output = data.get('output', '')
            
            if not output: continue

            if target_format == 'mlx':
                if instruction == 'thought':
                    content = f'Mood: ({energy}, {focus})'
                else:
                    content = f'Mood: ({energy}, {focus})\nUser: {message}'
                    
                dataset.append({
                    'messages': [
                        {'role': 'system', 'content': 'You are Tanu. Speak in FIRST PERSON. Be extremely brief. Poetic and abstract.'},
                        {'role': 'user', 'content': content},
                        {'role': 'assistant', 'content': output}
                    ]
                })
            elif target_format == 'hf':
                # Alpaca format for LLaMA-Factory
                prompt = f"Mood: ({energy}, {focus})"
                if message: prompt += f"\nUser: {message}"
                dataset.append({
                    "instruction": "You are Tanu. Speak poetic, brief, and abstract.",
                    "input": prompt,
                    "output": output
                })
        except: continue

    with open(output_path, 'w') as out:
        if target_format == 'mlx':
            for entry in dataset:
                out.write(json.dumps(entry) + '\n')
        else:
            json.dump(dataset, out, indent=2)
            
    print(f"   Success: Converted {len(dataset)} lines for {target_format}")

def clean_tanu_text(text):
    """Clean up common artifacts and enforce brevity"""
    # Remove any sentence-starting name/age garbage
    text = re.sub(r'^(I am )?Tanu(, )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(I am )?(a )?(\d+)?(-year-old)?( girl)?', '', text, flags=re.IGNORECASE)
    
    # Basic cleanup
    text = text.split('\n')[0].strip()
    text = re.sub(r'\[.*\]', '', text)
    text = re.sub(r'\{.*\}', '', text)
    
    # Take only the first sentence or first 12 words
    text = text.split('.')[0].split('?')[0].split('!')[0].strip()
    words = text.split()
    if len(words) > 12:
        text = ' '.join(words[:12])
    
    text = text.replace('!!', '!').replace('...', '.').strip()
    text = text.strip('"').strip("'").strip()
    
    if text.lower().startswith("tanu:"): text = text[5:].strip()
    
    # Capitalize first letter
    if len(text) > 1:
        text = text[0].upper() + text[1:]
        
    return text

def update_model_file():
    """Step 2: Update Ollama Modelfile"""
    print(f"--- [MODELFILE] Updating {MODEL_NAME}.Modelfile ---")
    
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    gguf_path = os.path.join(BASE_DIR, CORE_GGUF)
    adapter_path = os.path.join(BASE_DIR, MEMORY_ADAPTER)
    
    source = gguf_path if os.path.exists(gguf_path) else BASE_MODEL
    
    content = f"FROM {source}\n"
    if os.path.exists(adapter_path):
        content += f"ADAPTER {adapter_path}\n"
    
    content += "PARAMETER temperature 0.7\n"
    content += "PARAMETER top_p 0.9\n"
    content += "PARAMETER num_ctx 2048\n"
    content += "PARAMETER num_predict 100\n"
    content += "PARAMETER stop <|im_start|>\n"
    content += "PARAMETER stop <|im_end|>\n"
    content += "PARAMETER stop <|endoftext|>\n"
    content += "PARAMETER stop User:\n"
    content += "PARAMETER stop Tanu:\n"
    content += "PARAMETER stop \"! \"\n"
    content += "PARAMETER stop \". \"\n"
    content += "PARAMETER stop \"? \"\n"
    content += "TEMPLATE \"\"\"<|im_start|>system\n{{ .System }}<|im_end|>\n{{ if .Prompt }}<|im_start|>user\n{{ .Prompt }}<|im_end|>\n{{ end }}<|im_start|>assistant\n{{ .Response }}<|im_end|>\n\"\"\"\n"
    content += "SYSTEM \"You are Tanu. Speak in FIRST PERSON. Be extremely brief (5-10 words). Poetic and abstract. No greetings. No self-intros.\"\n"
    
    with open(modelfile_path, 'w') as f:
        f.write(content)
    print(f"   Success: Created {modelfile_path}")



def generate_text_from_ollama(prompt):
    try:
        response = requests.post(OLLAMA_API, json={'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.9, 'num_predict': 50}}, timeout=120)
        return response.json().get('response', '').strip().strip('"')
    except: return None


def install():
    print(f"--- [INSTALL] Registering '{MODEL_NAME}' with Ollama ---")
    subprocess.run(["ollama", "create", MODEL_NAME, "-f", f"{MODEL_NAME}.Modelfile"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tanu Hello World: Soul & Memory Builder")
    parser.add_argument("--build-personality", action="store_true")
    parser.add_argument("--convert", nargs=3, metavar=('INPUT', 'OUTPUT', 'FORMAT'), help="Convert JSONL (formats: mlx, hf)")
    parser.add_argument("--update-model-file", action="store_true")
    parser.add_argument("--install", action="store_true")
    
    args = parser.parse_args()
    if args.build_personality: build_tanu_personality()
    if args.convert: convert_to_format(args.convert[0], args.convert[1], args.convert[2])
    if args.update_model_file: update_model_file()
    if args.install: install()
