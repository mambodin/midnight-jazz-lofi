import os
import re
import shutil
import subprocess
from pathlib import Path

BASE_DIR  = Path(os.path.expanduser('~/youtube-pipeline'))
QUEUE_DIR = BASE_DIR / "thumbnails" / "queue"
USED_DIR  = BASE_DIR / "thumbnails" / "used"
OUT_PATH  = BASE_DIR / "thumbnails" / "current_thumb.jpg"
FONT_PATH = "/usr/share/fonts/truetype/bebas-neue/BebasNeue-Regular.ttf"
MIN_QUEUE = 5


def _sanitize_drawtext(text):
    """Keep only characters safe for FFmpeg drawtext inline text= value."""
    return re.sub(r"[^A-Z0-9 ]", "", text.upper())


def pick_thumbnail(title_line1="MIDNIGHT JAZZ", title_line2="LOFI BEATS"):
    """
    Pick oldest PNG from queue, add Bebas Neue text overlay, save as JPEG.

    Returns (rendered_thumb_path, source_png_path).
    The source PNG is NOT moved — caller must move it to thumbnails/used/
    after confirming upload succeeded.

    Raises FileNotFoundError if queue is empty.
    """
    USED_DIR.mkdir(parents=True, exist_ok=True)
    queue_files = sorted(QUEUE_DIR.glob("*.png"))

    if not queue_files:
        raise FileNotFoundError(
            "Thumbnail queue is empty! "
            "Upload Midjourney images to thumbnails/queue/ "
            "using: scp thumb_*.png ubuntu@YOUR_VPS:~/youtube-pipeline/thumbnails/queue/"
        )

    if len(queue_files) <= MIN_QUEUE:
        print(f"WARNING: Only {len(queue_files)} thumbnails left — generate more soon!", flush=True)

    src   = queue_files[0]
    line1 = _sanitize_drawtext(title_line1)
    line2 = _sanitize_drawtext(title_line2)

    drawtext = (
        f"drawtext=fontfile={FONT_PATH}:"
        f"text='{line1}':"
        f"fontsize=68:fontcolor=white:"
        f"x=60:y=h-155:"
        f"shadowcolor=black@0.7:shadowx=2:shadowy=2,"
        f"drawtext=fontfile={FONT_PATH}:"
        f"text='{line2}':"
        f"fontsize=38:fontcolor=white@0.85:"
        f"x=60:y=h-90:"
        f"shadowcolor=black@0.6:shadowx=1:shadowy=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", (
            f"scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            f"{drawtext}"
        ),
        "-q:v", "2",
        str(OUT_PATH)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg thumbnail error: {result.stderr[-500:]}", flush=True)
        raise RuntimeError("Thumbnail generation failed")

    print(f"Thumbnail ready: {OUT_PATH.name} (source: {src.name})", flush=True)
    return str(OUT_PATH), str(src)


def move_thumbnail_to_used(source_path):
    """Move the source PNG to thumbnails/used/ after a successful upload."""
    src = Path(source_path)
    USED_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), USED_DIR / src.name)
    print(f"Thumbnail archived: {src.name} → used/", flush=True)


if __name__ == "__main__":
    result = pick_thumbnail("90 MIN JAZZ LOFI", "RAINY TOKYO NIGHT")
    thumb_path, src_path = result
    print(f"Output: {thumb_path}")
    print(f"Source: {src_path}")
    print("(source not moved — call move_thumbnail_to_used() after upload)")
