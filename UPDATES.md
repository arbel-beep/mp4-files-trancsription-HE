# Updates

All notable changes to this project, newest first.

---

## 2026-06-09 (3)

### Cost tracking for OpenAI Whisper API

When using the paid OpenAI option (`transcribe_openai.py`), you now see exactly
how much each file cost and a running total at the end of the session.

**Per file:**
```
[DONE] Saved: output/lecture_01.txt  |  47.3 min  ->  cost: $0.2838
```

**End of session:**
```
[COST] Total spent this session: $0.5964 (estimate)
[COST] Verify actual charges: https://platform.openai.com/usage
```

Cost is calculated from actual audio duration × the Whisper API rate
($0.006/min). Since OpenAI does not return billing info in the API response,
the number is an estimate — the link at the end takes you to your OpenAI
dashboard to verify exact charges.

---

## 2026-06-09 (2)

### Claude slash commands for transcription

Two `/transcribe` commands are now included for users running this project
inside [Claude Code](https://claude.ai/code):

- **`/transcribe`** — interactive session: asks which folder and which engine
  (local or OpenAI), runs the transcription, and saves a history summary to
  memory so future sessions can show what was already done.

- **`/transcribe-watch`** — auto-loop: asks for a folder once, then scans
  every 4.5 minutes and automatically transcribes any new MP4s it finds.
  Runs until you close the terminal.

No setup required — the commands live in `.claude/commands/` and are picked
up automatically by Claude Code.

---

## 2026-06-09

### Progress monitoring during transcription

Local transcription (`transcribe_local.py`) now shows live progress while a
video is being transcribed — no more staring at a frozen terminal wondering
whether it's still running.

**What you'll see:**

- An audio progress bar that fills as segments are processed
- File counter when transcribing a batch — e.g. `[3/10]`
- Audio duration printed upfront so you know what you're dealing with
- A real-time factor at the end of each file — e.g. `1.95x RT` means the
  10-second video was processed in ~5 seconds; on a slow CPU you might see
  something like `0.3x RT`

**No changes to how you run it** — same commands as before. Requires `tqdm`
(added to `requirements.txt`; run `pip install -r transcription/requirements.txt`
if you haven't updated your environment yet).

---

## Earlier

Initial release — video splitter, local transcriber, OpenAI Whisper API
transcriber, Windows launcher (`start.bat`).
