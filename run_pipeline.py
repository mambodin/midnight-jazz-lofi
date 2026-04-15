"""
Midnight Jazz Lofi — Daily Pipeline Master Script
Runs all 7 steps to generate and upload one video automatically.

Usage:
    python3 -u run_pipeline.py

Scheduled via crontab:
    0 9 * * * cd /home/ubuntu/youtube-pipeline && /home/ubuntu/youtube-pipeline/venv/bin/python3 -u run_pipeline.py >> /home/ubuntu/youtube-pipeline/logs/pipeline_$(date +\%Y\%m\%d).log 2>&1
"""
import os
import sys
import shutil
import random
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

sys.path.insert(0, os.path.expanduser('~/youtube-pipeline/scripts'))

from generate_metadata import generate_metadata
from generate_music import generate_music_batch
from assemble_audio import assemble_audio, get_duration
from generate_video import generate_video
from assemble_video import assemble_video
from pick_thumbnail import pick_thumbnail, move_thumbnail_to_used
from upload_youtube import upload_video

# ── Config ────────────────────────────────────────────────────────────────────
NUM_TRACKS    = 20       # tracks per video
VIDEO_PRIVACY = "public" # must be one of: public, private, unlisted
BASE_DIR      = Path(os.path.expanduser('~/youtube-pipeline'))
OUTPUT_DIR    = BASE_DIR / "output"
LOG_DIR       = BASE_DIR / "logs"

assert VIDEO_PRIVACY in {"public", "private", "unlisted"}, \
    f"Invalid VIDEO_PRIVACY: {VIDEO_PRIVACY!r} — must be public, private, or unlisted"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

MIN_FREE_BYTES = 2 * 1024 ** 3  # 2 GB


def check_disk_space():
    usage = shutil.disk_usage(BASE_DIR)
    free_gb = usage.free / (1024 ** 3)
    if usage.free < MIN_FREE_BYTES:
        raise RuntimeError(
            f"Insufficient disk space: {free_gb:.1f} GB free — need at least 2 GB"
        )
    log.info(f"Disk space OK: {free_gb:.1f} GB free")


def cleanup_output():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in OUTPUT_DIR.glob("music/track_*.mp3"):
        f.unlink()
    for f in OUTPUT_DIR.glob("final_audio.mp3"):
        f.unlink()
    for f in OUTPUT_DIR.glob("final_video.mp4"):
        f.unlink()
    for f in OUTPUT_DIR.glob("video/*.mp4"):
        f.unlink()
    log.info("Cleaned up previous output files")


def run():
    start = datetime.now()
    log.info("=" * 50)
    log.info("MIDNIGHT JAZZ LOFI — DAILY PIPELINE STARTING")
    log.info(f"Run date: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 50)

    mood_idx  = random.randint(0, 4)
    scene_idx = random.randint(0, 4)
    log.info(f"Selected mood: {mood_idx}, scene: {scene_idx}")

    try:
        # Step 1: Disk space + cleanup
        log.info("\n[1/7] Pre-flight checks and cleanup...")
        check_disk_space()
        cleanup_output()

        # Step 2: Generate music
        log.info(f"\n[2/7] Generating {NUM_TRACKS} music tracks...")
        tracks = generate_music_batch(
            style_index=mood_idx,
            num_tracks=NUM_TRACKS,
            output_dir=str(OUTPUT_DIR / "music")
        )
        if not tracks:
            raise RuntimeError("No tracks generated")
        min_required = max(1, int(NUM_TRACKS * 0.8))
        if len(tracks) < min_required:
            raise RuntimeError(
                f"Too many tracks failed: {len(tracks)}/{NUM_TRACKS} succeeded "
                f"(minimum {min_required} required)"
            )
        log.info(f"Generated {len(tracks)}/{NUM_TRACKS} tracks")

        # Step 3: Assemble audio
        log.info("\n[3/7] Assembling audio...")
        audio_path = assemble_audio(
            track_paths=tracks,
            output_path=str(OUTPUT_DIR / "final_audio.mp3")
        )
        log.info(f"Audio assembled: {audio_path}")

        # Step 4: Generate metadata (uses real audio duration)
        audio_duration_mins = int(get_duration(audio_path) / 60)
        log.info(f"\n[4/7] Generating metadata ({audio_duration_mins} min)...")
        meta = generate_metadata(
            mood_index=mood_idx,
            scene_index=scene_idx,
            duration_mins=audio_duration_mins
        )
        log.info(f"Title: {meta['title']}")

        # Step 5: Generate video clip
        log.info("\n[5/7] Generating video clip...")
        video_clip = generate_video(
            scene_index=scene_idx,
            output_dir=str(OUTPUT_DIR / "video")
        )
        if not video_clip:
            raise RuntimeError("Video generation failed")
        log.info(f"Video clip: {video_clip}")

        # Step 6: Assemble final video
        log.info("\n[6/7] Assembling final video...")
        final_video = assemble_video(
            audio_path=audio_path,
            video_clip_path=video_clip,
            output_path=str(OUTPUT_DIR / "final_video.mp4")
        )
        log.info(f"Final video: {final_video}")

        # Step 7: Thumbnail + upload
        log.info("\n[7/7] Picking thumbnail and uploading...")
        thumb_path = None
        thumb_src  = None
        try:
            thumb_path, thumb_src = pick_thumbnail(
                title_line1=meta["short_title"],
                title_line2=meta["scene_label"]
            )
            log.info(f"Thumbnail: {thumb_path}")
        except FileNotFoundError as e:
            log.warning(f"Thumbnail queue empty: {e}")

        # Cap hashtags in description to 3 (YouTube topic hashtag limit)
        hashtags = "\n".join(
            f"#{t.replace(' ', '')}" for t in meta["tags"][:3]
        )
        description = meta["description"] + "\n\n" + hashtags

        video_id = upload_video(
            video_path=final_video,
            title=meta["title"],
            description=description,
            tags=meta["tags"],
            thumbnail_path=thumb_path,
            category_id="10",
            privacy=VIDEO_PRIVACY
        )

        # Only archive thumbnail after a confirmed successful upload
        if thumb_src:
            move_thumbnail_to_used(thumb_src)

        elapsed = int((datetime.now() - start).total_seconds() // 60)
        log.info("\n" + "=" * 50)
        log.info("PIPELINE COMPLETE")
        log.info(f"Video ID:  {video_id}")
        log.info(f"URL:       https://www.youtube.com/watch?v={video_id}")
        log.info(f"Duration:  {elapsed} minutes")
        log.info("=" * 50)

        return video_id

    except Exception as e:
        log.error(f"\nPIPELINE FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
