---
description: Transcribe MP4 recordings to text. Checks memory for history, lists untranscribed files, asks which folder and engine, runs the script, then saves results to memory.
---

You are helping the user transcribe MP4 recordings (Hebrew) to text.

Project root: the current working directory (where this repo is cloned)
Scripts:      `transcription/` subfolder
Output:       `output/` subfolder

---

## Step 1 — Check memory for recent history

Search memory for past transcription sessions so you can inform the user:

```
/memory-search transcription history --namespace tasks
```

If results exist, briefly surface them: "Last time: [folder] was transcribed with OpenAI on 2026-05-10, 6 files, 0 errors."
If no history, skip silently.

---

## Step 2 — Ask the user for the videos folder

Ask: "Which folder contains the MP4 files you want to transcribe?"

Accept a full path. Then scan that folder recursively for MP4s that do NOT have a matching .txt in the `output/` folder.

Show a summary:
```
Found 4 MP4 files pending transcription in: <folder>
  - lecture_01.mp4
  - lecture_02.mp4
  - lecture_03.mp4
  - lecture_04.mp4
```

If all files already have transcripts, tell the user and stop.

---

## Step 3 — Ask which engine

1. Which engine?
   - **local** — faster-whisper on CPU, no cost, slower. Good Hebrew with `large-v3`. Use `medium` for speed.
   - **openai** — OpenAI Whisper API, fast, ~$0.006/min, needs API key in `transcription/.env`

2. If local: which model? (default: `medium`)
   - `tiny` / `base` / `small` / `medium` / `large-v3`

---

## Step 4 — Run transcription

**Local:**
```
py -3 transcription/transcribe_local.py "<folder_path>" --model <model>
```

**OpenAI:**
```
py -3 transcription/transcribe_openai.py "<folder_path>"
```

Note the start time, which files were saved, and any errors.

---

## Step 5 — Save results to memory

After transcription completes, store a summary:

```
npx @claude-flow/cli@latest memory store \
  --key "transcription-<folder-name>-<YYYY-MM-DD>" \
  --value "Folder: <name> | Engine: <local|openai> | Model: <model> | Files: <N saved> / <N total> | Errors: <list or none> | Duration: ~<Xmin>" \
  --namespace tasks
```

This lets future `/transcribe` sessions show history without rescanning everything.
