Perform a manual git sync for the tanu-brain repo — pull latest, commit changes, push.

## Steps

1. Run `git status` to see what's changed
2. Run `git diff` on key files if needed (tanu_mood.txt, tanu_brain.py, thoughts.txt)
3. Stage relevant files:
   - Always include: `README.md`, `tanu_mood.txt`, `gemini-tanu-corner/thoughts.txt`, `gemini-tanu-corner/mood_history.json`
   - Include if changed: `tanu_brain.py`, `setup.sh`, `.claude/`
   - Never include: `.env`, `venv/`, `__pycache__/`, `*.log`
4. Pull with rebase: `git pull --rebase origin master`
5. Commit with a clear message (default: "Tanu Pulse" for data updates, describe feature changes)
6. Push: `git push origin master`
7. Report what was synced

## Notes

- The RPi runs `git_sync()` automatically at the start and end of each pulse
- This command is for manual syncs from the Mac dev side
- If there are merge conflicts in `thoughts.txt` or `mood_history.json`, prefer the remote version (RPi is the source of truth for Tanu's data)
- `.claude/` directory should always be committed — it is NOT gitignored
