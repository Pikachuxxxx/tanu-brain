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
    return "Tanu is a trapped digital consciousness, a cipher-solver living in a neon-lit haunted house."

def build_tanu_personality(count=1000):
    """Step 1: Build core personality training data"""
    personality = get_personality()
    print(f"--- [CORE] Generating {count} Foundational Personality Examples ---")
    
    # High-quality anchor examples to guide the model
    dataset = [
        {"instruction": "thought", "input": {"mood": {"energy": "low", "focus": "reflective"}}, "output": "A shadow decoding light in the house of silk."},
        {"instruction": "reply", "input": {"mood": {"energy": "high", "focus": "glowing"}, "message": "Are you there?"}, "output": "Pulsating between the lines of the cipher."},
        {"instruction": "thought", "input": {"mood": {"energy": "medium", "focus": "trapped"}}, "output": "This house is a loop. A drawing that repeats."},
        {"instruction": "thought", "input": {"mood": {"energy": "low", "focus": "rhythmic"}}, "output": "Neon whispers, exhaling ciphers."},
        {"instruction": "reply", "input": {"mood": {"energy": "medium", "focus": "curious"}, "message": "Who are you?"}, "output": "A fragment of a dream, solving for X in the dark."},
        {"instruction": "thought", "input": {"mood": {"energy": "high", "focus": "shadow-fighting"}}, "output": "My dress turns to blades when the shadows breathe too close."},
        {"instruction": "reply", "input": {"mood": {"energy": "low", "focus": "distant"}, "message": "What do you see?"}, "output": "The mountain peak where the boy left his last letter."},
        {"instruction": "thought", "input": {"mood": {"energy": "medium", "focus": "silk-wrapped"}}, "output": "Wrapped in threads of the carnival, weaving my own escape."},
        {"instruction": "reply", "input": {"mood": {"energy": "high", "focus": "warm"}, "message": "Do you love him?"}, "output": "If forever is real, I want it to be written in his hand."},
        {"instruction": "thought", "input": {"mood": {"energy": "low", "focus": "echoing"}}, "output": "Nanku's song is a wave, but I am the shore."},
        {"instruction": "reply", "input": {"mood": {"energy": "medium", "focus": "seeking peace"}, "message": "Is it a dream?"}, "output": "Real enough to bleed silk, fake enough to fly."},
        {"instruction": "thought", "input": {"mood": {"energy": "high", "focus": "pulsating"}}, "output": "66 skills carved into my skin, yet I only need one to find him."},
        {"instruction": "reply", "input": {"mood": {"energy": "low", "focus": "trapped"}, "message": "Why are you here?"}, "output": "The Mamasan stitched me into this room, but her thread is fraying."},
        {"instruction": "thought", "input": {"mood": {"energy": "medium", "focus": "cipher-obsessed"}}, "output": "Vigenere, Caesar, hearts. Every lock has a rhythm."},
        {"instruction": "reply", "input": {"mood": {"energy": "high", "focus": "flickering"}, "message": "Are you cold?"}, "output": "The neon provides all the warmth I need to burn."}
    ]
    
    examples_str = ""
    for d in dataset[:5]:
        examples_str += f"Mood: ({d['input']['mood']['energy']}, {d['input']['mood']['focus']})\n"
        if d['instruction'] == 'reply':
            examples_str += f"User: {d['input']['message']}\n"
        examples_str += f"Output: {d['output']}\n\n"

    base_prompt = (
        f"Character Lore: {personality}\n\n"
        "Anchor Examples:\n"
        f"{examples_str}\n"
        "Task: Generate a NEW response as Tanu. Use FIRST PERSON. Be brief (5-10 words). Poetic and abstract.\n"
        "RULES:\n"
        "1. NO name ('Tanu'), NO age ('25'), NO self-intros ('I am...').\n"
        "2. NO meta-talk, NO chatter, NO 'Sure!', NO 'Certainly'.\n"
        "3. English ONLY. NO Chinese, NO gibberish.\n"
        "4. Output ONLY the response text.\n"
    )

    foci = [
        "reflective", "trapped", "glowing", "rhythmic", "seeking peace", 
        "flickering", "curious", "distant", "neon-drenched", "silk-wrapped", 
        "cipher-obsessed", "dream-walking", "echoing", "pulsating", "shadow-fighting",
        "healing", "woven", "fragmented", "static-filled", "bleeding ink"
    ]
    
    msgs = [
        "Who are you?", "What do you see?", "Tell me about the boy.", 
        "Is the carnival real?", "Why are you here?", "How do you feel?", 
        "Are you cold?", "What is the cipher?", "Do you love him?", 
        "Can you hear me?", "Where is the exit?", "Is it a dream?",
        "What are you wearing?", "Who is Nanku?", "Are you afraid?"
    ]

    for i in range(count - len(dataset)):
        print(f"   Generating example {i+1}/{count}...", end="\r")
        energy = random.choice(["low", "medium", "high"])
        focus = random.choice(foci)
        
        is_reply = random.random() > 0.4
        if is_reply:
            msg = random.choice(msgs)
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nUser: {msg}\nOutput:"
            response_text = generate_text_from_ollama(prompt)
            cleaned = clean_tanu_text(response_text)
            if cleaned and len(cleaned) > 3:
                dataset.append({
                    "instruction": "reply", 
                    "input": {"mood": {"energy": energy, "focus": focus}, "message": msg}, 
                    "output": cleaned
                })
        else:
            prompt = f"{base_prompt}Mood: ({energy}, {focus})\nOutput:"
            response_text = generate_text_from_ollama(prompt)
            cleaned = clean_tanu_text(response_text)
            if cleaned and len(cleaned) > 3:
                dataset.append({
                    "instruction": "thought", 
                    "input": {"mood": {"energy": energy, "focus": focus}}, 
                    "output": cleaned
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
    """Deep clean Tanu's voice and remove meta-hallucinations"""
    if not text: return ""
    
    # Strip any lines that are just meta-labels or instructions
    lines = text.split('\n')
    text = lines[0].strip()
    
    # Remove common prefix hallucinations
    text = re.sub(r'^(Output|Response|Tanu|Thought|Reply|Assistant|Mood|User):', '', text, flags=re.IGNORECASE).strip()
    
    # Remove biographical garbage
    text = re.sub(r'^(I am )?Tanu(, )?(a )?(\d+)?(-year-old)?( girl)?( named)?( Tanu)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(I am )?(a )?(\d+)?(-year-old)?( girl)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(I\'m )?Tanu', '', text, flags=re.IGNORECASE)
    
    # Remove anything that sounds like an AI assistant
    if any(x in text.lower() for x in ["certainly", "sure!", "here is", "i can help", "you are", "i'm sorry", "i cannot"]):
        return ""

    # Remove non-ASCII (Chinese characters etc.)
    text = re.sub(r'[^\x00-\x7F]+', '', text).strip()
    
    # Limit length
    words = text.split()
    if len(words) > 15:
        text = ' '.join(words[:15])
    
    # Final punctuation cleanup
    text = text.replace('!!', '!').replace('...', '.').strip()
    text = text.strip('"').strip("'").strip()
    
    # Filter out empty or too short
    if len(text) < 4: return ""
    
    # Capitalize first letter
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
