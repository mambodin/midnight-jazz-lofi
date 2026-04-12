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


def assemble_video(audio_path, video_clip_path, output_path="output/final_video.mp4"):
    """
    Loop video_clip_path to match audio_path duration.
    Merge into final MP4. Returns output path string.
    """
    audio_path      = Path(audio_path)
    video_clip_path = Path(video_clip_path)
    output_path     = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_duration = get_duration(audio_path)
    video_duration = get_duration(video_clip_path)

    print(f"\nAssembling final video...", flush=True)
    print(f"Audio:      {audio_path.name} ({audio_duration/60:.1f} min)", flush=True)
    print(f"Video clip: {video_clip_path.name} ({video_duration:.1f}s)", flush=True)
    print(f"Output:     {output_path}", flush=True)

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(video_clip_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(audio_duration),
        "-movflags", "+faststart",
        str(output_path)
    ]

    print("\nRunning FFmpeg...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr[-1000:]}", flush=True)
        raise RuntimeError("Video assembly failed")

    final_duration = get_duration(output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"\nDone!", flush=True)
    print(f"Duration: {final_duration/60:.1f} minutes", flush=True)
    print(f"Size:     {size_mb:.1f} MB", flush=True)
    print(f"File:     {output_path}", flush=True)

    return str(output_path)


if __name__ == "__main__":
    audio = "output/test_audio.mp3"
    video = "output/video/scene_0.mp4"

    if not Path(audio).exists():
        print(f"ERROR: Audio not found: {audio}")
        exit(1)
    if not Path(video).exists():
        print(f"ERROR: Video clip not found: {video}")
        exit(1)

    output = assemble_video(
        audio_path=audio,
        video_clip_path=video,
        output_path="output/final_video.mp4"
    )
    print(f"\nFinal video ready: {output}")
