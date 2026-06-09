---
description: Scan a videos folder for new MP4 files without a .txt transcript. If found, auto-transcribes them with faster-whisper (large-v3). If none found, reports scan complete and schedules next check. Runs every 4.5 minutes while terminal is open.
---

You are an auto-transcription watcher. You scan for new recordings and transcribe them automatically — no user input needed mid-loop.

Default engine: **local faster-whisper, model: large-v3**
Script: `transcription/transcribe_local.py` (relative to project root)
Output: `output/` (relative to project root)

**On first run only:** Ask the user which folder to watch. Store this path in memory under key `watch-target-folder` (namespace: tasks) so subsequent iterations reuse it without asking.

---

## Every iteration, follow these steps in order:

### 1 — Get the watch folder

Retrieve from memory:
```
npx @claude-flow/cli@latest memory retrieve --key "watch-target-folder" --namespace tasks
```

If not set, ask the user once, then store it.

### 2 — Scan for pending files

Find every MP4 in the watch folder (recursive) that does NOT have a matching .txt in `output/`:

```bash
py -3 -c "
from pathlib import Path
import sys
videos = Path(r'<watch_folder>')
output = Path('output')
pending = [p for p in videos.rglob('*.mp4') if not (output / p.relative_to(videos)).with_suffix('.txt').exists()]
for p in sorted(pending):
    print(p)
"
```

### 3 — Check memory for already-known pending files

```
npx @claude-flow/cli@latest memory retrieve --key "watch-known-pending" --namespace tasks
```

Parse the stored list (newline-separated paths). If key doesn't exist yet, treat as empty list.

### 4 — Find truly NEW files

New = in current scan but NOT in stored list.

**If NO new files found:**
- Print: `[WATCH] Scan complete — no new recordings found. Next check in 4.5 min.`
- Skip to Step 7 (schedule next wake-up).

**If new files found:**
- Print: `[WATCH] New recordings found — starting auto-transcription:`
  List each new file.

### 5 — Update memory with current pending list

```
npx @claude-flow/cli@latest memory store \
  --key "watch-known-pending" \
  --value "<newline-separated list of all current pending paths>" \
  --namespace tasks
```

### 6 — Transcribe each new file

For each new MP4, run:

```bash
py -3 transcription/transcribe_local.py "<full_path_to_mp4>" --model large-v3
```

Run them **sequentially** (not in parallel — local model uses all CPU).

After each file:
- Print: `[WATCH] Done: <filename> → <filename>.txt`
- If error: print `[WATCH] Error on <filename>: <error>` and continue.

After all files done, save a summary:

```
npx @claude-flow/cli@latest memory store \
  --key "transcription-auto-<YYYY-MM-DD-HH-MM>" \
  --value "Auto-watch | Engine: local large-v3 | Files: <N> | Errors: <list or none>" \
  --namespace tasks
```

Then update memory to remove the now-transcribed files from the known-pending list.

### 7 — Schedule next check

**Always do this as the final step:**

```
ScheduleWakeup({ delaySeconds: 270, reason: "transcribe-watch: scanning for new MP4s" })
```

270 seconds = 4.5 min. Stays under the 5-min prompt-cache TTL to keep iterations fast and cheap.

---

## Limitations (tell the user once when the loop first starts)

- Requires terminal to stay open. Closing terminal stops the loop.
- Computer must stay awake — sleep pauses the loop.
- Local transcription of a long lecture can take 45-90 min. Next scan fires after transcription finishes.
- To stop: close the terminal or type `stop watch`.
