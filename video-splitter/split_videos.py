"""
Split oversized MP4 files into parts using ffmpeg (cross-platform — Windows/Mac/Linux).

Usage:
    python split_videos.py <folder>            # split any *.mp4 over 200MB into <name>/<name>_partNNN.mp4
    python split_videos.py <folder> --fix      # re-split any existing parts still over 200MB

Requires ffmpeg and ffprobe on PATH.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LIMIT_MB = 200
SPLIT_TARGET_MB = 120   # conservative: keyframe alignment can overshoot by ~40%
FIX_TARGET_MB = 80


def require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"[ERROR] '{tool}' not found on PATH. Install ffmpeg first.")
            sys.exit(1)


def mb(num_bytes: int) -> float:
    return num_bytes / 1048576


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def segment(src: Path, out_pattern: Path, seg_seconds: int):
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-c", "copy", "-map", "0",
         "-segment_time", str(seg_seconds), "-f", "segment", "-reset_timestamps", "1", str(out_pattern)],
        capture_output=True,
    )


def split_oversized(folder: Path):
    mp4s = sorted(folder.glob("*.mp4"))
    if not mp4s:
        print("[INFO] No MP4 files found in folder root.")
        return

    for f in mp4s:
        size_mb = mb(f.stat().st_size)
        if size_mb <= LIMIT_MB:
            print(f"SKIP: {f.name} ({size_mb:.0f}MB) already under {LIMIT_MB}MB")
            continue

        duration = probe_duration(f)
        seg_dur = int(SPLIT_TARGET_MB * duration / size_mb)

        print(f"\n==> {f.name}")
        print(f"    Size: {size_mb:.0f}MB | Duration: {duration:.0f}s | Segment: ~{seg_dur}s each")

        out_dir = folder / f.stem
        out_dir.mkdir(exist_ok=True)
        segment(f, out_dir / f"{f.stem}_part%03d.mp4", seg_dur)

        print("    Done. Checking part sizes:")
        for part in sorted(out_dir.glob("*.mp4")):
            part_mb = mb(part.stat().st_size)
            flag = " <-- OVER LIMIT!" if part_mb > LIMIT_MB else ""
            print(f"      {part_mb:.1f}MB  {part.name}{flag}")

    print("\nAll done.")


def fix_oversized(folder: Path):
    limit_bytes = LIMIT_MB * 1048576
    any_found = False

    for sub_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        for part in sorted(sub_dir.glob("*.mp4")):
            size_bytes = part.stat().st_size
            if size_bytes <= limit_bytes:
                continue
            any_found = True
            size_mb = mb(size_bytes)
            print(f"OVER: {part} ({size_mb:.1f}MB) -- re-splitting...")

            duration = probe_duration(part)
            seg_dur = int(FIX_TARGET_MB * duration / size_mb)

            tmp_dir = part.with_name(part.stem + "_resplit")
            tmp_dir.mkdir(exist_ok=True)
            segment(part, tmp_dir / f"{part.stem}_%03d.mp4", seg_dur)

            new_parts = sorted(tmp_dir.glob("*.mp4"))
            still_over = False
            for newpart in new_parts:
                nb = newpart.stat().st_size
                flag = ""
                if nb > limit_bytes:
                    flag = " <-- STILL OVER!"
                    still_over = True
                print(f"  {mb(nb):.1f}MB  {newpart.name}{flag}")

            if not still_over:
                part.unlink()
                for newpart in new_parts:
                    newpart.rename(sub_dir / newpart.name)
                tmp_dir.rmdir()
                print(f"  Replaced {part}")
            else:
                print(f"  WARNING: re-split still has oversized parts in {tmp_dir}. Manual intervention needed.")

    if not any_found:
        print("[INFO] No oversized parts found.")
        return

    print("\nFix pass done. Final sizes:")
    for sub_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        print(f"  --- {sub_dir.name} ---")
        for part in sorted(sub_dir.glob("*.mp4")):
            size_bytes = part.stat().st_size
            flag = " <-- OVER!" if size_bytes > limit_bytes else ""
            print(f"    {mb(size_bytes):.1f}MB  {part.name}{flag}")


def main():
    parser = argparse.ArgumentParser(description="Split oversized MP4s with ffmpeg (cross-platform)")
    parser.add_argument("folder", help="Folder containing MP4 files")
    parser.add_argument("--fix", action="store_true",
                        help="Re-split any already-split parts still over the size limit")
    args = parser.parse_args()

    require_ffmpeg()
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[ERROR] Folder not found: {folder}")
        sys.exit(1)

    if args.fix:
        fix_oversized(folder)
    else:
        split_oversized(folder)


if __name__ == "__main__":
    main()
