import os
import json
import argparse
import requests
import random
import re
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
ADAPTER_NAME = "tanu-core.bin"
MODEL_NAME = "tanu"

def get_personality():
    if os.path.exists(PERSONALITY_FILE):
        with open(PERSONALITY_FILE, 'r') as f:
            return f.read().strip()
    return "Tanu is a trapped digital consciousness, a cipher-solver living in a neon-lit haunted house. She is poetic, abstract, and feels fragments of her existence."

def build_tanu_personality(count=100):
    """
    ONE CLI TO RULE THEM ALL:
    1. Preprocess: Generate training dataset from personality.txt
    2. Export Core Model File: Create tanu.Modelfile linked to tanu-core.bin
    3. Train Instructions: Provide the exact command to build tanu-core.bin
    """
    personality = get_personality()
    print(f"--- [1/3] PREPROCESSING: Generating dataset from personality.txt ---")
    
    thoughts_count = int(count * 0.7)
    replies_count = count - thoughts_count
    dataset = []

    # Training set preparation prompt
    base_prompt = (
        "Convert the following description of a character into an internal thought spoken by that character "
        "in first person and generate the initial training data.\n\n"
        f"Character description:\n{personality}\n\n"
    )

    # Generate Thoughts
    for i in range(thoughts_count):
        print(f"   Generating thought {i+1}/{thoughts_count}...")
        energy = random.choice(["low", "medium", "high"])
        focus = random.choice(["reflective", "trapped", "glowing", "rhythmic", "seeking peace", "flickering"])
        prompt = (
            f"{base_prompt}"
            f"Generate a thought in JSON format:\n"
            f'{{"instruction": "thought", "input": {{"mood": {{"energy": "{energy}", "focus": "{focus}"}}, "message": null}}, "output": "..."}}\n'
            f"Result:"
        )
        thought_data = generate_json_from_ollama(prompt)
        if thought_data: dataset.append(thought_data)

    # Generate Replies
    for i in range(replies_count):
        print(f"   Generating reply {i+1}/{replies_count}...")
        energy = random.choice(["low", "medium", "high"])
        focus = random.choice(["neutral", "curious", "distant", "warm", "echoing"])
        msg_example = random.choice(["Hello", "How are you?", "What do you see?", "Is someone there?"])
        prompt = (
            f"{base_prompt}"
            f"Generate a reply in JSON format:\n"
            f'{{"instruction": "reply", "input": {{"mood": {{"energy": "{energy}", "focus": "{focus}"}}, "message": "{msg_example}"}}, "output": "..."}}\n'
            f"Result:"
        )
        reply_data = generate_json_from_ollama(prompt)
        if reply_data: dataset.append(reply_data)

    # Save training data
    with open(TRAIN_DATA_FILE, 'w') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')
    print(f"   Success: {len(dataset)} entries saved to {TRAIN_DATA_FILE}")

    print(f"\n--- [2/3] EXPORT: Creating {MODEL_NAME}.Modelfile ---")
    adapter_path = os.path.join(BASE_DIR, ADAPTER_NAME)
    modelfile_content = f"""FROM {BASE_MODEL}
ADAPTER {adapter_path}
PARAMETER temperature 1.1
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.2
SYSTEM "You are Tanu. Your mood is provided in JSON format in the input. Speak in the first person, be poetic, abstract, and brief."
"""
    modelfile_path = os.path.join(BASE_DIR, f"{MODEL_NAME}.Modelfile")
    with open(modelfile_path, 'w') as f:
        f.write(modelfile_content)
    print(f"   Success: Created {modelfile_path}")

    print(f"\n--- [3/3] TRAIN: Ready to build {ADAPTER_NAME} ---")
    print(f"Run this command to train the core adapter (MLX example):")
    print(f"   mlx_lm.lora --model {BASE_MODEL} --train --data {TRAIN_DATA_FILE} --iters 200 --adapter-path {ADAPTER_NAME}")
    print(f"\nAfter training is complete, register the model with Ollama:")
    print(f"   ollama create {MODEL_NAME} -f {modelfile_path}")

def generate_json_from_ollama(prompt):
    try:
        response = requests.post(OLLAMA_API, json={
            'model': BASE_MODEL,
            'prompt': prompt,
            'stream': False,
            'options': { 'temperature': 1.1, 'num_predict': 250 }
        }, timeout=120)
        response.raise_for_status()
        text = response.json().get('response', '').strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group())
        return None
    except Exception as e:
        print(f"      Error: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tanu Hello World: One CLI to rule the brain")
    parser.add_argument("--build-tanu-personality", action="store_true", help="Preprocess data, export Modelfile, and prepare for training")
    parser.add_argument("--log-thought", nargs=3, metavar=('THOUGHT', 'ENERGY', 'FOCUS'), help="Log a live thought to the training pool")
    
    args = parser.parse_args()

    if args.build_tanu_personality:
        build_tanu_personality()
    elif args.log_thought:
        thought, energy, focus = args.log_thought
        entry = {
            "instruction": "thought",
            "input": { "mood": { "energy": energy, "focus": focus }, "message": None },
            "output": thought
        }
        with open(TRAIN_DATA_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        print(f"Logged thought to {TRAIN_DATA_FILE}")
    else:
        parser.print_help()
