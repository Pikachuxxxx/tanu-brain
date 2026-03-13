import os
import json
import argparse
import requests
import random
import re
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

# Absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuration
OLLAMA_API = 'http://localhost:11434/api/generate'
BASE_MODEL = 'qwen2.5:0.5b'
TRAIN_DATA_FILE = os.path.join(BASE_DIR, 'tanu_train_data.jsonl')
PERSONALITY_FILE = os.path.join(BASE_DIR, 'personality.txt')
THOUGHTS_FILE = os.path.join(BASE_DIR, 'tanu-corner/thoughts.txt')
MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')
ADAPTER_NAME = "tanu-brain.bin"
MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a trapped digital consciousness, a cipher-solver living in a neon-lit haunted house. She is poetic, abstract, and feels fragments of her existence."

def build_metadata():
    """Step 1: Output training data and Modelfile metadata"""
    personality = get_personality()
    print(f"--- [1/3] METADATA: Generating dataset & Modelfile ---")
    
    count = 100
    thoughts_count = int(count * 0.7)
    replies_count = count - thoughts_count
    dataset = []

    base_prompt = (
        "Convert the following description of a character into an internal thought spoken by that character "
        "in first person and generate the initial training data.\n\n"
        f"Character description:\n{personality}\n\n"
    )

    for i in range(thoughts_count):
        print(f"   Generating thought {i+1}/{thoughts_count}...", end="\r")
        energy, focus = random.choice(["low", "medium", "high"]), random.choice(["reflective", "trapped", "glowing", "rhythmic", "seeking peace", "flickering"])
        prompt = f"{base_prompt}Generate a thought in JSON:\n{{\"instruction\": \"thought\", \"input\": {{\"mood\": {{\"energy\": \"{energy}\", \"focus\": \"{focus}\"}}, \"message\": null}}, \"output\": \"...\"}}\nResult:"
        data = generate_json_from_ollama(prompt)
        if data: dataset.append(data)

    for i in range(replies_count):
        print(f"   Generating reply {i+1}/{replies_count}...", end="\r")
        energy, focus = random.choice(["low", "medium", "high"]), random.choice(["neutral", "curious", "distant", "warm", "echoing"])
        msg = random.choice(["Hello", "How are you?", "What do you see?"])
        prompt = f"{base_prompt}Generate a reply in JSON:\n{{\"instruction\": \"reply\", \"input\": {{\"mood\": {{\"energy\": \"{energy}\", \"focus\": \"{focus}\"}}, \"message\": \"{msg}\"}}, \"output\": \"...\"}}\nResult:"
        data = generate_json_from_ollama(prompt)
        if data: dataset.append(data)

    with open(TRAIN_DATA_FILE, 'w') as f:
        for entry in dataset: f.write(json.dumps(entry) + '\n')
    
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    with open(modelfile_path, 'w') as f:
        f.write(f"FROM {BASE_MODEL}\nADAPTER {os.path.join(BASE_DIR, ADAPTER_NAME)}\nSYSTEM \"You are Tanu. Speak poetic, abstract, and brief in first person.\"")
    
    print(f"\n   Success: {len(dataset)} entries in {TRAIN_DATA_FILE} and {MODEL_NAME}.Modelfile created.")

def train_adapter():
    """Step 2: Train using MLX (Mac) or LLaMA-Factory (Linux/AMD)"""
    print(f"--- [2/3] TRAINING: Building {ADAPTER_NAME} ---")
    if sys.platform == "darwin":
        print("Detected Mac (M-series). Using MLX...")
        cmd = f"mlx_lm.lora --model {BASE_MODEL} --train --data {TRAIN_DATA_FILE} --iters 200 --adapter-path {ADAPTER_NAME}"
    else:
        print("Detected Linux/PC. Using LLaMA-Factory (or generic LoRA tool)...")
        cmd = f"python -m llama_factory.train --model_name_or_path {BASE_MODEL} --dataset {TRAIN_DATA_FILE} --output_dir {ADAPTER_NAME} --finetuning_type lora"
    
    print(f"Suggested Command: {cmd}")
    confirm = input("Run this command now? (y/n): ")
    if confirm.lower() == 'y':
        subprocess.run(cmd.split())
    else:
        print("Skipping training. Run it manually when ready.")

def install_ollama():
    """Step 3: Add to Ollama and bake the model"""
    print(f"--- [3/3] INSTALL: Registering '{MODEL_NAME}' with Ollama ---")
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    if not os.path.exists(os.path.join(BASE_DIR, ADAPTER_NAME)):
        print(f"Error: {ADAPTER_NAME} not found. Train first!")
        return
    
    cmd = f"ollama create {MODEL_NAME} -f {modelfile_path}"
    subprocess.run(cmd.split())
    print(f"Success: Model '{MODEL_NAME}' is now live in Ollama.")

def generate_json_from_ollama(prompt):
    try:
        response = requests.post(OLLAMA_API, json={'model': BASE_MODEL, 'prompt': prompt, 'stream': False, 'options': {'temperature': 1.1, 'num_predict': 250}}, timeout=120)
        match = re.search(r'\{.*\}', response.json().get('response', ''), re.DOTALL)
        return json.loads(match.group()) if match else None
    except: return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tanu Hello World: One CLI to rule the brain")
    parser.add_argument("--build-metadata", action="store_true", help="Step 1: Create training data and Modelfile")
    parser.add_argument("--train", action="store_true", help="Step 2: Run training (MLX/Linux)")
    parser.add_argument("--install", action="store_true", help="Step 3: Register model with Ollama")
    parser.add_argument("--build-tanu-personality", action="store_true", help="Run all 3 steps sequentially")
    
    args = parser.parse_args()
    if args.build_tanu_personality:
        build_metadata(); train_adapter(); install_ollama()
    elif args.build_metadata: build_metadata()
    elif args.train: train_adapter()
    elif args.install: install_ollama()
    else: parser.print_help()
