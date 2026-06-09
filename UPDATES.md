# Updates

All notable changes to this project, newest first.

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
