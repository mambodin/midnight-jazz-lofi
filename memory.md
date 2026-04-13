# Midnight Jazz Lofi — Project Memory File
_Last updated: 2026-04-12_

---

## 1. Project overview

**Goal:** Build a fully automated AI faceless YouTube channel to monetize via AdSense, Spotify, and music licensing.

- **Channel name:** Midnight Jazz Lofi
- **Handle:** @midnightjazzlofi
- **Niche:** Dark lofi / lo-fi jazz — cinematic, late night, study music
- **Location:** Singapore

---

## 2. Tool stack & monthly costs

| Tool | Purpose | Cost |
|------|---------|------|
| Suno Pro | Music generation, 500 songs/mo, commercial rights | $10/mo |
| Kling Standard | Video clips, 660 credits/mo | $10/mo |
| Midjourney Basic | Thumbnails, manual Sunday batch | $10/mo |
| Anthropic Claude API | Metadata (title/desc/tags) via Haiku | ~$0.09/mo |
| Tencent Cloud Lighthouse | VPS Singapore region | $0.84/mo yr1 ($10.08/yr promo) |
| n8n (self-hosted) | Workflow orchestration | Free |
| **Total** | | **~$31/mo** |

---

## 3. Cost per video

~$0.76–$1.00 using subscriptions:
- Suno: $0.02–0.24 (8–12 tracks)
- Kling: $0.50–0.53 (1 looping clip)
- FFmpeg: ~$0.02 (VPS compute)
- Claude API: ~$0.003
- VPS amortised: ~$0.17

No fal.ai — using Midjourney manually instead.

---

## 4. Pipeline architecture

Automated daily pipeline on VPS (7 steps):

1. Claude API generates metadata (title / description / tags)
2. Suno API generates 8–12 music tracks → MP3 files
3. FFmpeg concatenates tracks → single 60–90 min MP3
4. Kling API generates 5–10 sec looping video clip → MP4
5. FFmpeg loops clip to match audio duration → final 1080p MP4
6. `pick_thumbnail.py` picks oldest MJ image from queue + adds Bebas Neue text overlay via FFmpeg
7. YouTube Data API v3 uploads with all metadata + thumbnail

Orchestrated by Linux cron job: `0 9 * * *` (daily 9am SGT)

---

## 5. VPS setup

- **Provider:** Tencent Cloud Lighthouse, Singapore region
- **OS:** Ubuntu 22.04
- **IP:** 129.226.215.31
- **Project folder:** `~/youtube-pipeline/`
- **Subfolders:** `scripts/`, `thumbnails/queue/`, `thumbnails/used/`, `output/`, `logs/`
- **Key scripts:** `generate_metadata.py`, `generate_music.py`, `assemble_audio.py`, `generate_video.py`, `assemble_video.py`, `pick_thumbnail.py`, `upload_youtube.py`, `run_pipeline.py`
- **Auth:** `.env` file stores all API keys (never committed to git)
- **Python venv:** `anthropic`, `google-api-python-client`, `google-auth-oauthlib`, `requests`, `python-dotenv`, `pyjwt`, `Pillow`
- **n8n:** Running in Docker on port 5678, `N8N_SECURE_COOKIE=false`

---

## 6. Brand — 5 visual scenes (Kling prompts)

All scenes use: **STATIC CAMERA, locked off tripod shot, no camera movement**

1. Rainy Tokyo alley — neon reflections in wet cobblestones, dim lamplight
2. Dimly lit jazz bar — amber spotlight, cigarette smoke, empty stage
3. City rooftop — rain, neon glow below, fog, lone empty chair
4. Late night cafe — rain on window, coffee cup, open book, blurred city lights
5. Noir detective office — desk lamp, venetian blinds, whiskey glass, city rain

**Kling settings:** model: kling-v1-6, mode: std, duration: 5, cfg_scale: 0.3
**Negative prompt:** camera movement, panning, zooming, tilting, shaking, handheld, dolly, tracking shot

---

## 7. Brand — 5 music moods (Suno prompts)

- **A:** Slow dark jazz lofi, brushed drums, upright bass, muted trumpet, 70bpm melancholic
- **B:** Rainy night beats, lo-fi hip-hop, vinyl crackle, soft piano, distant saxophone, 80bpm
- **C:** Cinematic noir jazz, brooding double bass, sparse guitar, atmospheric piano, 65bpm
- **D:** Smooth dark jazz lofi, mid-tempo 90bpm, clean guitar, light percussion brushwork
- **E:** Winter jazz lofi, cold sparse piano, 72bpm minor key, distant string pads

Suno API endpoint: `https://api.sunoapi.org/api/v1/generate`
Poll endpoint: `GET /api/v1/generate/record-info?taskId=xxx`
Status flow: `PENDING → TEXT_SUCCESS → FIRST_SUCCESS → SUCCESS`
Audio URL field: `data.response.sunoData[0].sourceAudioUrl`

---

## 8. Thumbnail system

- **Tool:** Midjourney Basic $10/mo
- **Workflow:** Manual Sunday batch — 20 min/week
- **MJ suffix for all prompts:** `--style raw --ar 16:9 --v 7 --q 2 --s 750`
- **Discord:** Private server with 5 channels (one per scene)
- **Process:** Generate 4 variants → upscale best → download → rename `thumb_001.png` sequentially → `scp` to `~/youtube-pipeline/thumbnails/queue/`
- **Buffer:** Keep 14+ images in queue (2 weeks)
- **Overlay:** `pick_thumbnail.py` adds Bebas Neue font text via FFmpeg
- **Font path:** `/usr/share/fonts/truetype/bebas-neue/BebasNeue-Regular.ttf`

---

## 9. YouTube API setup

- **Google Cloud project:** `youtube-lofi-pipeline`
- **API:** YouTube Data API v3 enabled
- **Auth:** OAuth 2.0 Desktop App credentials
- **Files:** `client_secret.json` + `token.json` on VPS (gitignored)
- **Token generation:** Run `scripts/get_token.py` once
- **Quota:** 10,000 units/day free — `videos.insert` = 1,600 units = max 6 uploads/day
- **Category ID:** 10 (Music)

---

## 10. Channel brand details

**Color palette:**
- `#0d0d14` Void (background)
- `#1a1025` Dark plum
- `#ff6b35` Neon ember (accent)
- `#4ecdc4` Neon teal
- `#c9a96e` Amber gold
- `#8b8fa8` Mist blue

**SEO title format:** `[Duration] [mood] [use case] | [visual vibe]`
**Core hashtags:** `#lofi #jazzlofi #darklofi #studymusic #focusmusic #lofijazz #chillbeats #midnightvibes`
**Video length:** 60–90 min (more ad slots, more watch time per view)
**Upload schedule:** Daily 9am SGT via cron job

---

## 11. 5-phase roadmap

| Phase | Timeline | Status |
|-------|---------|--------|
| Phase 1: Setup & accounts | Week 1 | ✅ DONE |
| Phase 2: Build pipeline scripts | Week 2–3 | ✅ DONE |
| Phase 3: Content strategy + automation | Week 3–4 | ✅ DONE |
| Phase 4: Launch & grow | Month 1–6 | 🔄 NEXT |
| Phase 5: Monetize & scale | Month 6–12 | ⏳ Pending |

**All 6 pipeline scripts working:** `generate_metadata.py`, `generate_music.py`, `assemble_audio.py`, `generate_video.py`, `assemble_video.py`, `upload_youtube.py`
**Master script:** `run_pipeline.py`
**Cron job:** `0 9 * * *` SGT

---

## 12. Monetization strategy

| Stream | Details | Timeline |
|--------|---------|---------|
| YouTube AdSense | RPM $4 conservative / $8–11 optimistic | YPP at 1K subs + 4K watch hours |
| Spotify / Apple Music | DistroKid $22.99/yr | Anytime (needs Suno commercial license) |
| Music licensing | Pond5 / Artlist, $15–50/license | After 100+ tracks |
| Channel memberships | Exclusive playlists perk | At 500 subs |
| Affiliate links | Headphones, study apps | Immediately |
| Sponsorships | $50–200/integration | At 5K–10K subs |

**Break-even projected:** Month 8–9

---

## 13. Known issues & fixes

**sunoapi.org hCaptcha:** Showed "too many requests" during signup. Fix: complete captcha on mobile data. Alternatives: `udioapi.pro` or `acedata.cloud`.

**Kling shaky video:** Fixed by adding `STATIC CAMERA, locked off tripod shot, no camera movement` to all prompts. `cfg_scale` lowered to 0.3. Negative prompt includes all camera movement types.

**n8n port 5678:** Required `N8N_SECURE_COOKIE=false` env var. Container needed `chown -R 1000:1000 ~/.n8n` and `-u 1000:1000` flag.

**YouTube OAuth on VPS:** Used `urn:ietf:wg:oauth:2.0:oob` redirect URI with manual code paste since VPS has no browser.

---

## 14. Pipeline status

- **First test video:** https://www.youtube.com/watch?v=cpx8eWaIX3Y (private)
- **Runtime:** 29 minutes for 10 tracks
- **VIDEO_PRIVACY:** Currently `private` — change to `public` in `run_pipeline.py` when ready
- **Thumbnail queue:** Needs real Midjourney images — currently using black placeholder
- **Cron job:** Running, fires daily 9am SGT
- **GitHub repo:** Created as `midnight-jazz-lofi` zip — ready to push

---

## 15. Next actions (Phase 4)

1. Change `VIDEO_PRIVACY = "public"` in `run_pipeline.py`
2. Make first video public in YouTube Studio
3. Upload real Midjourney thumbnails to queue (Sunday batch)
4. Create YouTube playlists: Study Sessions, Late Night Focus, Sleep Music
5. Post 2–3 YouTube Shorts cut from first video
6. Set up DistroKid for Spotify distribution
7. Check analytics after 48 hours (target CTR >4%, avg view duration >30%)
8. Push code to GitHub repo
