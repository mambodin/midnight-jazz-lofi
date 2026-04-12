import os
import json
import subprocess
from pathlib import Path


def get_duration(file_path):
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", str(file_path)
    ], capture_output=True, text=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def assemble_audio(track_paths, output_path="output/final_audio.mp3"):
    if not track_paths:
        raise ValueError("No tracks provided")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for track in track_paths:
            abs_path = Path(track).resolve()
            f.write(f"file '{abs_path}'\n")

    print(f"\nAssembling {len(track_paths)} tracks into {output_path}...", flush=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr}", flush=True)
        raise RuntimeError("Audio assembly failed")

    concat_file.unlink()

    duration_secs = get_duration(output_path)
    duration_mins = duration_secs / 60
    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"Done: {output_path}", flush=True)
    print(f"Duration: {duration_mins:.1f} minutes", flush=True)
    print(f"Size: {size_mb:.1f} MB", flush=True)

    return str(output_path)


if __name__ == "__main__":
    test_track = "output/music/track_01.mp3"
    if not Path(test_track).exists():
        print(f"Test track not found: {test_track}")
        print("Run generate_music.py first")
        exit(1)

    fake_batch = [test_track, test_track, test_track]
    output = assemble_audio(fake_batch, output_path="output/test_audio.mp3")
    print(f"\nTest assembly saved to: {output}")
