"""
Transcribe MP4 files using OpenAI Whisper API.

Usage:
    python transcribe_openai.py <folder_or_file> [output_dir]

Examples:
    python transcribe_openai.py "C:/path/to/videos/subject-folder"
    python transcribe_openai.py "C:/path/to/video.mp4"
    python transcribe_openai.py "C:/path/to/videos" "C:/path/to/transcripts"

Transcripts are written to output_dir (default: ./output next to this script),
mirroring the input folder structure, so you can point any tool (Notion importer,
upload script, etc.) at one place and pick what to do with the .txt files.
Skips any MP4 whose output .txt already exists.
"""
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

MODEL = "whisper-1"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"
WHISPER_PRICE_PER_MINUTE = 0.006  # OpenAI Whisper API pricing (USD), check openai.com/pricing for current rate
MAX_MB = 25
CHUNK_MINUTES = 10
RETRY_ATTEMPTS = 5
RETRY_BASE_DELAY = 2.0
FFMPEG_TIMEOUT = 1800

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY missing in transcription/.env")

client = OpenAI(api_key=API_KEY)


def run_ffmpeg(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffmpeg timed out after {FFMPEG_TIMEOUT}s") from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "ffmpeg failed")


def extract_audio(mp4_path: Path, output_mp3: Path):
    print(f"[INFO] Extracting audio: {mp4_path.name}")
    run_ffmpeg(["ffmpeg", "-y", "-i", str(mp4_path), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(output_mp3)])


def split_audio(audio_path: Path, chunks_dir: Path):
    output_pattern = chunks_dir / "chunk_%03d.mp3"
    run_ffmpeg(["ffmpeg", "-y", "-i", str(audio_path), "-f", "segment",
                "-segment_time", str(CHUNK_MINUTES * 60), "-c", "copy", str(output_pattern)])
    chunks = sorted(chunks_dir.glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("No chunks created")
    return chunks


def transcribe_file(file_path: Path):
    print(f"[INFO] Uploading: {file_path.name} ({file_path.stat().st_size / 1048576:.1f} MB)")
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            print(f"[INFO] Attempt {attempt}/{RETRY_ATTEMPTS}: {file_path.name}")
            with open(file_path, "rb") as f:
                response = client.audio.transcriptions.create(model=MODEL, file=f)
            text = getattr(response, "text", "").strip()
            if not text:
                raise RuntimeError(f"Empty transcript for {file_path.name}")
            return text
        except (APIConnectionError, APITimeoutError) as e:
            if attempt == RETRY_ATTEMPTS:
                raise RuntimeError(f"Failed after {RETRY_ATTEMPTS} attempts: {e}") from e
            delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), 30.0)
            print(f"[WARN] {type(e).__name__} — retrying in {delay:.1f}s")
            time.sleep(delay)
        except (AuthenticationError, RateLimitError, APIStatusError, Exception) as e:
            raise RuntimeError(f"{type(e).__name__}: {e}") from e


def probe_duration_seconds(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return 0.0


def estimate_and_confirm(mp4s, root: Path, output_dir: Path) -> bool:
    pending = [m for m in mp4s if not output_path_for(m, root, output_dir).exists()]
    if not pending:
        print("[INFO] All files already have transcripts — nothing to do.")
        return False

    print(f"[INFO] Estimating audio length of {len(pending)} file(s) to transcribe (this can take a moment)...")
    total_minutes = sum(probe_duration_seconds(m) for m in pending) / 60
    est_cost = total_minutes * WHISPER_PRICE_PER_MINUTE
    print(f"[INFO] Total audio: ~{total_minutes:.1f} min  |  Estimated cost: ~${est_cost:.2f} "
          f"(OpenAI Whisper API @ ${WHISPER_PRICE_PER_MINUTE:.3f}/min — verify current rate at openai.com/pricing)")

    answer = input("[?] Proceed with transcription? [y/N]: ").strip().lower()
    if answer != "y":
        print("[INFO] Cancelled — no API calls made.")
        return False
    return True


def output_path_for(mp4_path: Path, root: Path, output_dir: Path) -> Path:
    try:
        rel = mp4_path.relative_to(root)
    except ValueError:
        rel = Path(mp4_path.name)
    return (output_dir / rel).with_suffix(".txt")


def process_one(mp4_path: Path, root: Path, output_dir: Path) -> float:
    """Returns the cost in USD for this file (0.0 if skipped)."""
    print(f"\n{'='*60}")
    print(f"[INFO] Processing: {mp4_path.name}")
    out = output_path_for(mp4_path, root, output_dir)
    if out.exists():
        print(f"[INFO] Skip — {out.name} already exists")
        return 0.0
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        audio = tmp / "audio.mp3"
        extract_audio(mp4_path, audio)
        size_mb = audio.stat().st_size / 1048576
        duration_min = probe_duration_seconds(audio) / 60

        if size_mb <= MAX_MB:
            print(f"[INFO] Small file ({size_mb:.1f} MB) — direct transcription")
            text = transcribe_file(audio)
        else:
            print(f"[INFO] Large file ({size_mb:.1f} MB) — splitting into chunks")
            chunks_dir = tmp / "chunks"
            chunks_dir.mkdir()
            chunks = split_audio(audio, chunks_dir)
            print(f"[INFO] {len(chunks)} chunk(s)")
            parts = []
            for i, chunk in enumerate(chunks, 1):
                print(f"[INFO] Chunk {i}/{len(chunks)}")
                parts.append(transcribe_file(chunk))
            text = "\n\n".join(parts)

    cost = duration_min * WHISPER_PRICE_PER_MINUTE
    out.write_text(text, encoding="utf-8")
    print(f"[DONE] Saved: {out}  |  {duration_min:.1f} min  →  cost: ${cost:.4f}")
    return cost


def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe_openai.py <folder_or_file> [output_dir]")
        sys.exit(1)

    target = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if target.is_file():
        cost = process_one(target, target.parent, output_dir)
        if cost > 0:
            print(f"\n[COST] Total spent this session: ${cost:.4f} (estimate)")
            print(f"[COST] Verify actual charges: https://platform.openai.com/usage")
    elif target.is_dir():
        mp4s = sorted(p for p in target.rglob("*.mp4") if "_part" not in p.stem)
        if not mp4s:
            print("[INFO] No MP4 files found.")
            sys.exit(0)
        print(f"[INFO] Found {len(mp4s)} MP4 file(s) in {target.name}")
        print(f"[INFO] Transcripts will be written to: {output_dir}")
        if not estimate_and_confirm(mp4s, target, output_dir):
            sys.exit(0)
        total_cost = 0.0
        for mp4 in mp4s:
            try:
                total_cost += process_one(mp4, target, output_dir)
            except Exception as e:
                print(f"[ERROR] {mp4.name}: {e}")
        if total_cost > 0:
            print(f"\n[COST] Total spent this session: ${total_cost:.4f} (estimate)")
            print(f"[COST] Verify actual charges: https://platform.openai.com/usage")
    else:
        print(f"[ERROR] Path not found: {target}")
        sys.exit(1)

    print("\n[ALL DONE]")


if __name__ == "__main__":
    main()
