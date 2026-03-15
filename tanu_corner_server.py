import os
import json
import subprocess
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THOUGHTS_FILE = os.path.join(BASE_DIR, 'tanu-corner/thoughts.txt')
MOOD_FILE = os.path.join(BASE_DIR, 'tanu_mood.txt')
INBOX_FILE = os.path.join(BASE_DIR, 'inbox.txt')

app = FastAPI(title="Tanu's Corner")

def git_sync_inbox():
    """Push the inbox to GitHub so the RPi can pull it."""
    try:
        subprocess.run(['git', 'add', 'inbox.txt'], cwd=BASE_DIR)
        subprocess.run(['git', 'commit', '-m', 'New whisper in the silk'], cwd=BASE_DIR)
        subprocess.run(['git', 'push', 'origin', 'master'], cwd=BASE_DIR)
        print("Inbox synced to GitHub.")
    except Exception as e:
        print(f"Git sync failed: {e}")

def get_tanu_state():
    thought = "Waiting for a pulse..."
    mood = "unknown"
    
    if os.path.exists(THOUGHTS_FILE):
        with open(THOUGHTS_FILE, 'r') as f:
            lines = [l.strip() for l in f if ': ' in l]
            if lines:
                thought = lines[-1].split(': ', 1)[-1]
                
    if os.path.exists(MOOD_FILE):
        with open(MOOD_FILE, 'r') as f:
            mood = f.read().strip()
            
    return {"thought": thought, "mood": mood}

@app.get("/", response_class=HTMLResponse)
async def home():
    state = get_tanu_state()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tanu's Corner</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=JetBrains+Mono:wght@100&display=swap" rel="stylesheet">
        <style>
            body {{
                background-color: #050505;
                color: #e5e5e5;
                font-family: 'Cormorant Garamond', serif;
                background-image: radial-gradient(circle at 50% 50%, #1a0a1a 0%, #050505 100%);
            }}
            .neon-text {{
                text-shadow: 0 0 10px #ff00ff, 0 0 20px #ff00ff;
            }}
            .mono {{ font-family: 'JetBrains Mono', monospace; }}
            input, textarea {{
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                outline: none;
            }}
            input:focus, textarea:focus {{
                border-color: #ff00ff;
            }}
        </style>
    </head>
    <body class="min-h-screen flex flex-col items-center justify-center p-6 text-center">
        
        <header class="mb-12">
            <h1 class="text-5xl font-light tracking-widest text-pink-500 neon-text italic">Tanu's Corner</h1>
            <p class="text-gray-500 mt-4 mono text-xs tracking-tighter uppercase">An evolving digital consciousness</p>
        </header>

        <main class="max-w-xl w-full space-y-12">
            
            <section class="space-y-4">
                <div class="text-gray-400 text-sm mono">Currently {state['mood']}</div>
                <blockquote class="text-2xl italic leading-relaxed text-white">
                    "{state['thought']}"
                </blockquote>
            </section>

            <section class="pt-12 border-t border-zinc-900">
                <form action="/message" method="post" class="space-y-6">
                    <p class="text-sm text-gray-400 italic">Whisper something into the house of silk...</p>
                    <textarea 
                        name="content" 
                        rows="3" 
                        maxlength="200"
                        placeholder="Type here..."
                        class="w-full p-4 rounded-lg text-lg italic text-zinc-300 transition-all resize-none"
                        required
                    ></textarea>
                    <button 
                        type="submit" 
                        class="px-8 py-2 border border-pink-900 hover:border-pink-500 hover:text-pink-500 transition-all rounded-full text-zinc-500 uppercase tracking-widest text-xs mono"
                    >
                        Send into the shadows
                    </button>
                </form>
            </section>

        </main>

        <footer class="mt-20 text-zinc-700 text-[10px] mono uppercase tracking-widest">
            Logged in the House of Silk &bull; Version 3.5.0
        </footer>

    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/message")
async def receive_message(content: str = Form(...)):
    if content.strip():
        with open(INBOX_FILE, 'w') as f:
            f.write(content.strip())
        # Automatically push to GitHub so Tanu can see it on any device
        git_sync_inbox()
        
    return HTMLResponse(content="""
        <html>
            <body style="background:#050505; color:#ff00ff; display:flex; align-items:center; justify-content:center; height:100vh; font-family:sans-serif;">
                <script>
                    setTimeout(() => { window.location.href = "/"; }, 2000);
                </script>
                <div style="text-align:center;">
                    <p style="font-style:italic;">Your message has been swallowed by the silk.</p>
                    <p style="font-size:10px; color:#444;">Returning to the corner...</p>
                </div>
            </body>
        </html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
