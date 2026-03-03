import subprocess
import os
import sys

# Thoughts should be passed as a single string argument
def gemini_think(thought):
    thought_file = "gemini-tanu-corner/gemini-tanu-corner.txt"
    os.makedirs(os.path.dirname(thought_file), exist_ok=True)
    
    with open(thought_file, "a") as f:
        f.write("\n--- Gemini Thought ---\n")
        f.write(f"{thought}\n")
    
    # Git operations
    try:
        subprocess.run(["git", "add", thought_file], check=True)
        subprocess.run(["git", "commit", "-m", "New Gemini thought about Tanu"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Thought recorded, committed, and pushed!")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        gemini_think(sys.argv[1])
    else:
        print("Usage: python3 gemini_think.py 'Your thought here'")
