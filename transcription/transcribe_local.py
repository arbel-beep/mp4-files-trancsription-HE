"""
Transcribe MP4 files locally using faster-whisper (no API key needed).

Usage:
    python transcribe_local.py <folder_or_file> [--model medium|large-v3] [--output-dir DIR]

Examples:
    python transcribe_local.py "C:/path/to/videos/subject-folder"
    python transcribe_local.py "C:/path/to/video.mp4" --model large-v3
    python transcribe_local.py "C:/path/to/videos" --output-dir "C:/path/to/transcripts"

Defaults: model=medium, language=he, device=cpu, compute_type=int8
Transcripts are written to --output-dir (default: ./output next to this script),
mirroring the input folder structure, so you can point any tool (Notion importer,
upload script, etc.) at one place and pick what to do with the .txt files.
Skips any MP4 whose output .txt already exists.
"""
import sys
import io
import time
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from faster_whisper import WhisperModel
from tqdm import tqdm

LANGUAGE = "he"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"


def load_model(model_size: str) -> WhisperModel:
    print(f"[INFO] Loading model: {model_size} (device={DEVICE}, compute={COMPUTE_TYPE})")
    return WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)


def output_path_for(mp4_path: Path, root: Path, output_dir: Path) -> Path:
    try:
        rel = mp4_path.relative_to(root)
    except ValueError:
        rel = Path(mp4_path.name)
    return (output_dir / rel).with_suffix(".txt")


def process_one(mp4_path: Path, model: WhisperModel, root: Path, output_dir: Path, file_index: int = 0, file_total: int = 1):
    out = output_path_for(mp4_path, root, output_dir)
    if out.exists():
        print(f"[INFO] Skip — {out.name} already exists")
        return
    out.parent.mkdir(parents=True, exist_ok=True)

    prefix = f"[{file_index}/{file_total}]" if file_total > 1 else ""
    print(f"\n{'='*60}")
    print(f"[INFO] {prefix} Transcribing: {mp4_path.name}")
    t_start = time.monotonic()
    segments, info = model.transcribe(str(mp4_path), language=LANGUAGE, beam_size=5)
    print(f"[INFO] Language: {info.language} (prob={info.language_probability:.2f}) | Audio: {info.duration:.1f}s")

    lines = []
    bar = tqdm(total=int(info.duration), unit="s", desc="audio", ncols=70, leave=False)
    last_end = 0.0
    for seg in segments:
        line = seg.text.strip()
        if line:
            lines.append(line)
            tqdm.write(f"  [{seg.start:.1f}s -> {seg.end:.1f}s] {line}")
        advance = seg.end - last_end
        if advance > 0:
            bar.update(int(advance))
        last_end = seg.end
    bar.close()

    elapsed = time.monotonic() - t_start
    rt_factor = info.duration / elapsed if elapsed > 0 else 0
    print(f"[DONE] {mp4_path.name} — {elapsed:.1f}s wall, {rt_factor:.2f}x RT | Saved: {out}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe MP4 files with faster-whisper")
    parser.add_argument("path", help="MP4 file or folder containing MP4 files")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: medium)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR),
                        help=f"Folder to write .txt transcripts to (default: {DEFAULT_OUTPUT_DIR})")
    args = parser.parse_args()

    target = Path(args.path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model(args.model)

    if target.is_file():
        process_one(target, model, target.parent, output_dir)
    elif target.is_dir():
        mp4s = sorted(p for p in target.rglob("*.mp4") if "_part" not in p.stem)
        if not mp4s:
            print("[INFO] No MP4 files found.")
            sys.exit(0)
        print(f"[INFO] Found {len(mp4s)} MP4 file(s) in {target.name}")
        print(f"[INFO] Transcripts will be written to: {output_dir}")
        for i, mp4 in enumerate(mp4s, 1):
            try:
                process_one(mp4, model, target, output_dir, file_index=i, file_total=len(mp4s))
            except Exception as e:
                print(f"[ERROR] {mp4.name}: {e}")
    else:
        print(f"[ERROR] Path not found: {target}")
        sys.exit(1)

    print("\n[ALL DONE]")


if __name__ == "__main__":
    main()
