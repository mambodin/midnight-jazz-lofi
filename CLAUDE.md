# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated YouTube channel pipeline for **Midnight Jazz Lofi** (@midnightjazzlofi). Generates dark jazz lofi music videos daily and uploads them via cron. Cost: ~$1/video, ~$31/month.

## Running the Pipeline

```bash
# Full pipeline (generates and uploads one video)
python3 -u run_pipeline.py

# Run individual scripts standalone (each has __main__ block)
python3 scripts/generate_metadata.py
python3 scripts/generate_music.py     # generates 1 test track
python3 scripts/generate_video.py     # generates 1 test clip
```

There are no tests or linting configured. No build step.

## System Dependencies

- **FFmpeg + FFprobe** — used by assemble_audio.py, assemble_video.py, and pick_thumbnail.py
- **Bebas Neue font** at `/usr/share/fonts/truetype/bebas-neue/BebasNeue-Regular.ttf` — used for thumbnail text overlay
- Python venv with `pip install -r requirements.txt`

## Architecture

**`run_pipeline.py`** is the master orchestrator. It runs 7 sequential steps, each delegating to a function in `scripts/`:

1. `generate_metadata()` — Calls Claude Haiku API to produce SEO title, description, tags as JSON
2. `cleanup_output()` — Deletes previous run's files from `output/`
3. `generate_music_batch()` — Calls Suno API to create 10 tracks sequentially (poll-based, ~10 min total)
4. `assemble_audio()` — FFmpeg concat demuxer joins tracks into `final_audio.mp3`
5. `generate_video()` — Calls Kling AI API to create a 5-sec looping clip (poll-based)
6. `assemble_video()` — FFmpeg loops the 5-sec clip with `-stream_loop -1` to match audio duration
7. `pick_thumbnail()` + `upload_video()` — Picks oldest PNG from queue, adds text overlay, uploads via YouTube Data API v3

### Key design details

- **All paths are hardcoded to `~/youtube-pipeline/`** — the repo is deployed there on a Tencent Lighthouse VPS (Singapore). `.env` is also loaded from that path.
- **5 mood/scene presets** (indices 0–4) are randomly selected each run. These indices are shared across `generate_metadata.py` (MOODS/SCENES arrays), `generate_music.py` (MUSIC_STYLES array), and `generate_video.py` (SCENE_PROMPTS array). They must stay in sync.
- **Suno and Kling use poll-based async** — submit task, then poll every 10s until complete/failed. Both have 60-attempt timeout (~10 min).
- **Kling JWT auth** — `generate_video.py` generates short-lived JWTs (30 min) from access/secret key pair using HS256.
- **Thumbnail queue** — Midjourney images are manually generated weekly and uploaded to `thumbnails/queue/`. Pipeline picks the oldest, adds Bebas Neue text overlay via FFmpeg drawtext filter, moves used images to `thumbnails/used/`. Warns when ≤5 remain.
- **YouTube OAuth** — `get_token.py` is a one-time interactive setup. `upload_youtube.py` auto-refreshes the token on each run.

## Environment Variables (`.env`)

`ANTHROPIC_API_KEY`, `SUNO_API_KEY`, `SUNO_CALLBACK_URL`, `KLING_ACCESS_KEY`, `KLING_SECRET_KEY`, `YOUTUBE_CLIENT_SECRET_PATH`, `YOUTUBE_TOKEN_PATH`

## Production Schedule

Daily at 9am SGT via crontab. Logs go to `~/youtube-pipeline/logs/pipeline_YYYYMMDD.log`.
