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
import random
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

sys.path.insert(0, os.path.expanduser('~/youtube-pipeline/scripts'))

from generate_metadata import generate_metadata
from generate_music import generate_music_batch
from assemble_audio import assemble_audio
from generate_video import generate_video
from assemble_video import assemble_video
from pick_thumbnail import pick_thumbnail
from upload_youtube import upload_video

# ── Config ────────────────────────────────────────────────────────────────────
NUM_TRACKS    = 20       # tracks per video (~60 min at 3 min/track)
VIDEO_PRIVACY = "public" # set to "private" for testing
BASE_DIR      = Path(os.path.expanduser('~/youtube-pipeline'))
OUTPUT_DIR    = BASE_DIR / "output"
LOG_DIR       = BASE_DIR / "logs"

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


def cleanup_output():
    for f in OUTPUT_DIR.glob("music/track_*.mp3"):
        f.unlink()
    for f in OUTPUT_DIR.glob("final_audio.mp3"):
        f.unlink()
    for f in OUTPUT_DIR.glob("final_video.mp4"):
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
        # Step 1: Generate metadata
        log.info("\n[1/7] Generating metadata...")
        meta = generate_metadata(
            mood_index=mood_idx,
            scene_index=scene_idx,
            duration_mins=int(NUM_TRACKS * 3)
        )
        log.info(f"Title: {meta['title']}")

        # Step 2: Clean up
        log.info("\n[2/7] Cleaning up previous run...")
        cleanup_output()

        # Step 3: Generate music
        log.info(f"\n[3/7] Generating {NUM_TRACKS} music tracks...")
        tracks = generate_music_batch(
            style_index=mood_idx,
            num_tracks=NUM_TRACKS,
            output_dir=str(OUTPUT_DIR / "music")
        )
        if not tracks:
            raise RuntimeError("No tracks generated")
        log.info(f"Generated {len(tracks)} tracks")

        # Step 4: Assemble audio
        log.info("\n[4/7] Assembling audio...")
        audio_path = assemble_audio(
            track_paths=tracks,
            output_path=str(OUTPUT_DIR / "final_audio.mp3")
        )
        log.info(f"Audio assembled: {audio_path}")

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
        try:
            thumb_path = pick_thumbnail(
                title_line1=meta["short_title"],
                title_line2=meta["scene_label"]
            )
            log.info(f"Thumbnail: {thumb_path}")
        except FileNotFoundError as e:
            log.warning(f"Thumbnail queue empty: {e}")
            thumb_path = None

        video_id = upload_video(
            video_path=final_video,
            title=meta["title"],
            description=meta["description"] + "\n\n" + "\n".join(
                f"#{t.replace(' ', '')}" for t in meta["tags"]
            ),
            tags=meta["tags"],
            thumbnail_path=thumb_path,
            category_id=meta.get("category_id", "10"),
            privacy=VIDEO_PRIVACY
        )

        elapsed = (datetime.now() - start).seconds // 60
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
