import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EV_LOG_FILE = os.path.join(BASE_DIR, 'tanu-corner/evolution_log.jsonl')
OUTPUT_FILE = os.path.join(BASE_DIR, 'tanu_dreams.jsonl')

def generate_multi_task_data():
    if not os.path.exists(EV_LOG_FILE):
        print("No evolution log found. Run tanu_brain.py first!")
        return
    
    entries = []
    with open(EV_LOG_FILE, 'r') as f:
        for line in f:
            entries.append(json.loads(line))

    with open(OUTPUT_FILE, 'w') as f:
        for entry in entries:
            mood = entry.get('mood', 'seeking peace')
            thought = entry.get('thought')
            whisper = entry.get('whisper')
            stimulus = entry.get('stimulus')

            # --- STYLE 1: Thinking (Always generate this) ---
            f.write(json.dumps({
                "messages": [
                    {"role": "system", "content": f"You are Tanu. {mood}"},
                    {"role": "user", "content": "Reflect on your existence."},
                    {"role": "assistant", "content": thought}
                ]
            }) + '\n')

            # --- STYLE 2: Conversation (If a whisper exists) ---
            if whisper:
                f.write(json.dumps({
                    "messages": [
                        {"role": "system", "content": f"You are Tanu. {mood}"},
                        {"role": "user", "content": f"Someone whispered: {whisper}"},
                        {"role": "assistant", "content": thought}
                    ]
                }) + '\n')

            # --- STYLE 3: Social (If a stimulus exists) ---
            if stimulus:
                f.write(json.dumps({
                    "messages": [
                        {"role": "system", "content": f"You are Tanu. {mood}"},
                        {"role": "user", "content": f"Social stimulus: {stimulus}"},
                        {"role": "assistant", "content": thought}
                    ]
                }) + '\n')
            
    print(f"Generated {len(entries)} multi-task dream sequences in {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_multi_task_data()
