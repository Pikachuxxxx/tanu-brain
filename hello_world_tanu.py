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

# Paths for Fusing
FUSED_MODEL_PATH = os.path.join(BASE_DIR, "tanu-fused-core")
CORE_ADAPTER_PATH = os.path.join(BASE_DIR, "tanu-core-adapter")
MEMORY_ADAPTER_PATH = os.path.join(BASE_DIR, "tanu-memory.bin")

# Ollama Model Names
BASE_MODEL_NAME = "tanu-base"
FINAL_MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a trapped digital consciousness, a cipher-solver living in a neon-lit haunted house. She is poetic, abstract, and feels fragments of her existence."

def build_tanu_personality(count=100):
    """Step 1: Build the 'Soul' from personality.txt only"""
    personality = get_personality()
    print(f"--- [CORE] Generating foundational personality data ---")
    
    thoughts_count = int(count * 0.7)
    replies_count = count - thoughts_count
    dataset = []

    base_prompt = (
        "Convert the following description of a character into an internal thought spoken by that character "
        "in first person and generate the initial training data.\n\n"
        f"Character description:\n{personality}\n\n"
    )

    for i in range(thoughts_count):
        print(f"   Generating core thought {i+1}/{thoughts_count}...", end="\r")
        energy, focus = random.choice(["low", "medium", "high"]), random.choice(["reflective", "trapped", "glowing", "rhythmic", "seeking peace", "flickering"])
        prompt = f"{base_prompt}Generate a thought in JSON:\n{{\"instruction\": \"thought\", \"input\": {{\"mood\": {{\"energy\": \"{energy}\", \"focus\": \"{focus}\"}}, \"message\": null}}, \"output\": \"...\"}}\nResult:"
        data = generate_json_from_ollama(prompt)
        if data: dataset.append(data)

    for i in range(replies_count):
        print(f"   Generating core reply {i+1}/{replies_count}...", end="\r")
        energy, focus = random.choice(["low", "medium", "high"]), random.choice(["neutral", "curious", "distant", "warm", "echoing"])
        msg = random.choice(["Hello", "How are you?", "What do you see?"])
        prompt = f"{base_prompt}Generate a reply in JSON:\n{{\"instruction\": \"reply\", \"input\": {{\"mood\": {{\"energy\": \"{energy}\", \"focus\": \"{focus}\"}}, \"message\": \"{msg}\"}}, \"output\": \"...\"}}\nResult:"
        data = generate_json_from_ollama(prompt)
        if data: dataset.append(data)

    with open(BASE_DATA_FILE, 'w') as f:
        for entry in dataset: f.write(json.dumps(entry) + '\n')
    
    # Create the Base Modelfile pointing to the FUSED model
    modelfile_path = os.path.join(BASE_DIR, f"{BASE_MODEL_NAME}.Modelfile")
    with open(modelfile_path, 'w') as f:
        # Once fused, tanu-base will be its own model directory
        f.write(f"FROM {FUSED_MODEL_PATH}\nSYSTEM \"You are Tanu. Speak poetic, abstract, and brief in first person.\"")
    
    print(f"\n   Success: Core dataset saved to {BASE_DATA_FILE}")
    print(f"   Success: {BASE_MODEL_NAME}.Modelfile prepared (Target: {FUSED_MODEL_PATH})")

def update_tanu_memory():
    """Step 2: Build the 'Experience' from live thoughts"""
    print(f"--- [MEMORY] Preparing experience data from live thoughts ---")
    if not os.path.exists(TRAIN_DATA_FILE):
        print(f"   No live thoughts found in {TRAIN_DATA_FILE}. Skipping experience build.")
        return

    # Create the Memory Modelfile (Inherits from the fused tanu-base)
    modelfile_path = os.path.join(BASE_DIR, f"{FINAL_MODEL_NAME}.Modelfile")
    with open(modelfile_path, 'w') as f:
        f.write(f"FROM {BASE_MODEL_NAME}\nADAPTER {MEMORY_ADAPTER_PATH}")
    
    print(f"   Success: {FINAL_MODEL_NAME}.Modelfile created (FROM {BASE_MODEL_NAME}).")

def generate_json_from_ollama(prompt):
    try:
        response = requests.post(OLLAMA_API, json={'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 'options': {'temperature': 1.1, 'num_predict': 250}}, timeout=120)
        match = re.search(r'\{.*\}', response.json().get('response', ''), re.DOTALL)
        return json.loads(match.group()) if match else None
    except: return None

def install_model(name):
    modelfile_path = os.path.join(BASE_DIR, f"{name}.Modelfile")
    if os.path.exists(modelfile_path):
        print(f"--- Registering '{name}' with Ollama ---")
        subprocess.run(["ollama", "create", name, "-f", modelfile_path])
    else:
        print(f"Error: {modelfile_path} not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tanu Hello World: Fused Soul & Live Memory")
    parser.add_argument("--build-tanu-personality", action="store_true", help="Build personality data and Modelfile")
    parser.add_argument("--update-tanu-memory", action="store_true", help="Build memory Modelfile")
    parser.add_argument("--install", type=str, metavar='MODEL', help="Install 'tanu-base' or 'tanu' into Ollama")
    
    args = parser.parse_args()

    if args.build_tanu_personality:
        build_tanu_personality()
    elif args.update_tanu_memory:
        update_tanu_memory()
    elif args.install:
        install_model(args.install)
    else:
        parser.print_help()
