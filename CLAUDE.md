# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated YouTube channel pipeline for **Midnight Jazz Lofi** (@midnightjazzlofi). Generates dark jazz lofi music videos daily and uploads them via cron. Cost: ~$1/video, ~$31/month.

- **Niche:** Dark lofi / lo-fi jazz — cinematic, late night, study music
- **Location:** Singapore
- **Video length:** 60–90 min (more ad slots, more watch time per view)
- **Upload schedule:** Daily 9am SGT via cron job

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

## Tool Stack & Monthly Costs

| Tool | Purpose | Cost |
|------|---------|------|
| Suno Pro | Music generation, 500 songs/mo, commercial rights | $10/mo |
| Kling Standard | Video clips, 660 credits/mo | $10/mo |
| Midjourney Basic | Thumbnails, manual Sunday batch | $10/mo |
| Anthropic Claude API | Metadata (title/desc/tags) via Haiku | ~$0.09/mo |
| Tencent Cloud Lighthouse | VPS Singapore region | $0.84/mo yr1 ($10.08/yr promo) |
| n8n (self-hosted) | Workflow orchestration | Free |
| **Total** | | **~$31/mo** |

## VPS Setup

- **Provider:** Tencent Cloud Lighthouse, Singapore region
- **OS:** Ubuntu 22.04
- **IP:** 129.226.215.31
- **Project folder:** `~/youtube-pipeline/`
- **Subfolders:** `scripts/`, `thumbnails/queue/`, `thumbnails/used/`, `output/`, `logs/`
- **n8n:** Running in Docker on port 5678, `N8N_SECURE_COOKIE=false`

## Environment Variables (`.env`)

`ANTHROPIC_API_KEY`, `SUNO_API_KEY`, `SUNO_CALLBACK_URL`, `KLING_ACCESS_KEY`, `KLING_SECRET_KEY`, `YOUTUBE_CLIENT_SECRET_PATH`, `YOUTUBE_TOKEN_PATH`

## Production Schedule

Daily at 9am SGT via crontab. Logs go to `~/youtube-pipeline/logs/pipeline_YYYYMMDD.log`.

## Brand — 5 Visual Scenes (Kling Prompts)

All scenes use: **STATIC CAMERA, locked off tripod shot, no camera movement**

1. Rainy Tokyo alley — neon reflections in wet cobblestones, dim lamplight
2. Dimly lit jazz bar — amber spotlight, cigarette smoke, empty stage
3. City rooftop — rain, neon glow below, fog, lone empty chair
4. Late night cafe — rain on window, coffee cup, open book, blurred city lights
5. Noir detective office — desk lamp, venetian blinds, whiskey glass, city rain

**Kling settings:** model: kling-v1-6, mode: std, duration: 5, cfg_scale: 0.3
**Negative prompt:** camera movement, panning, zooming, tilting, shaking, handheld, dolly, tracking shot

## Brand — 5 Music Moods (Suno Prompts)

- **A:** Slow dark jazz lofi, brushed drums, upright bass, muted trumpet, 70bpm melancholic
- **B:** Rainy night beats, lo-fi hip-hop, vinyl crackle, soft piano, distant saxophone, 80bpm
- **C:** Cinematic noir jazz, brooding double bass, sparse guitar, atmospheric piano, 65bpm
- **D:** Smooth dark jazz lofi, mid-tempo 90bpm, clean guitar, light percussion brushwork
- **E:** Winter jazz lofi, cold sparse piano, 72bpm minor key, distant string pads

Suno API endpoint: `https://api.sunoapi.org/api/v1/generate`
Poll endpoint: `GET /api/v1/generate/record-info?taskId=xxx`
Status flow: `PENDING → TEXT_SUCCESS → FIRST_SUCCESS → SUCCESS`
Audio URL field: `data.response.sunoData[0].sourceAudioUrl`

## Brand — Color Palette & SEO

| Color | Name |
|-------|------|
| `#0d0d14` | Void (background) |
| `#1a1025` | Dark plum |
| `#ff6b35` | Neon ember (accent) |
| `#4ecdc4` | Neon teal |
| `#c9a96e` | Amber gold |
| `#8b8fa8` | Mist blue |

**SEO title format:** `[Duration] [mood] [use case] | [visual vibe]`
**Core hashtags:** `#lofi #jazzlofi #darklofi #studymusic #focusmusic #lofijazz #chillbeats #midnightvibes`

## Thumbnail System

- **Tool:** Midjourney Basic $10/mo
- **Workflow:** Manual Sunday batch — 20 min/week
- **MJ suffix:** `--style raw --ar 16:9 --v 7 --q 2 --s 750`
- **Discord:** Private server with 5 channels (one per scene)
- **Process:** Generate 4 variants → upscale best → download → rename `thumb_001.png` sequentially → `scp` to `~/youtube-pipeline/thumbnails/queue/`
- **Buffer:** Keep 14+ images in queue (2 weeks)

## YouTube API Setup

- **Google Cloud project:** `youtube-lofi-pipeline`
- **API:** YouTube Data API v3 enabled
- **Auth:** OAuth 2.0 Desktop App credentials
- **Files:** `client_secret.json` + `token.json` on VPS (gitignored)
- **Token generation:** Run `scripts/get_token.py` once
- **Quota:** 10,000 units/day free — `videos.insert` = 1,600 units = max 6 uploads/day
- **Category ID:** 10 (Music)

## Known Issues & Fixes

- **sunoapi.org hCaptcha:** "Too many requests" during signup. Fix: complete captcha on mobile data. Alternatives: `udioapi.pro` or `acedata.cloud`.
- **Kling shaky video:** Fixed with `STATIC CAMERA` prompt prefix + `cfg_scale: 0.3` + negative prompt for all camera movement types.
- **n8n port 5678:** Required `N8N_SECURE_COOKIE=false`. Container needed `chown -R 1000:1000 ~/.n8n` and `-u 1000:1000`.
- **YouTube OAuth on VPS:** Used `urn:ietf:wg:oauth:2.0:oob` redirect URI with manual code paste (no browser on VPS).

## Monetization Strategy

| Stream | Details | Timeline |
|--------|---------|---------|
| YouTube AdSense | RPM $4 conservative / $8–11 optimistic | YPP at 1K subs + 4K watch hours |
| Spotify / Apple Music | DistroKid $22.99/yr | Anytime (needs Suno commercial license) |
| Music licensing | Pond5 / Artlist, $15–50/license | After 100+ tracks |
| Channel memberships | Exclusive playlists perk | At 500 subs |
| Affiliate links | Headphones, study apps | Immediately |
| Sponsorships | $50–200/integration | At 5K–10K subs |

**Break-even projected:** Month 8–9

## Roadmap & Status

| Phase | Timeline | Status |
|-------|---------|--------|
| Phase 1: Setup & accounts | Week 1 | Done |
| Phase 2: Build pipeline scripts | Week 2–3 | Done |
| Phase 3: Content strategy + automation | Week 3–4 | Done |
| Phase 4: Launch & grow | Month 1–6 | **Current** |
| Phase 5: Monetize & scale | Month 6–12 | Pending |

## Pipeline Status

- **First test video:** https://www.youtube.com/watch?v=cpx8eWaIX3Y (private)
- **Runtime:** ~29 minutes for 10 tracks
- **VIDEO_PRIVACY:** Currently `private` — change to `public` when ready
- **Thumbnail queue:** Needs real Midjourney images — currently using black placeholder
- **Cron job:** Running, fires daily 9am SGT

## Next Actions (Phase 4)

1. Change `VIDEO_PRIVACY = "public"` in `run_pipeline.py`
2. Make first video public in YouTube Studio
3. Upload real Midjourney thumbnails to queue (Sunday batch)
4. Create YouTube playlists: Study Sessions, Late Night Focus, Sleep Music
5. Post 2–3 YouTube Shorts cut from first video
6. Set up DistroKid for Spotify distribution
7. Check analytics after 48 hours (target CTR >4%, avg view duration >30%)
8. Push code to GitHub repo
