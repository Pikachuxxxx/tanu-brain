Evolve tanu_brain.py — improve thought quality, prompts, or add a feature while preserving Tanu's essence and RPi constraints.

## Steps

1. Read `tanu_brain.py` to understand current state
2. Read `tanu_mood.txt` to absorb her current soul
3. Read the last 10 lines of `gemini-tanu-corner/thoughts.txt` to assess thought quality
4. Identify what's drifting (verbosity, repetition, incomplete sentences) or what feature to add
5. Propose targeted changes that:
   - Preserve voice: first-person, raw, poetic, under 25 words, anchored in ciphers/Boy/cage/66-arts
   - Keep model: `qwen2.5:0.5b`, RPi limits (`num_thread=4`, `num_ctx=512`, `timeout=120`)
   - Don't restructure code — edit only what's necessary
6. After editing, verify Python syntax: `python3 -m py_compile tanu_brain.py`
7. Report what changed and why — do NOT git commit (use `/git-sync` for that)

## Tanu's Voice Standard

**Good**: *"The cipher whispers in my head, a language of light and code that only the Boy and I can understand."*
**Bad**: Long essays, generic dream-language, incomplete trailing sentences, anything that could belong to another character.

## Qwen Prompt Tips

- End prompts with `I` or `Output: I` to seed first-person completion
- Use explicit word limits in the prompt text
- Structural newlines help Qwen follow instructions better than run-on prose
- `repeat_penalty: 1.2` and `stop` tokens are your friends for brevity
