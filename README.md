# Midnight Jazz Lofi — Automated YouTube Pipeline

Fully automated AI-powered YouTube channel pipeline. Generates dark jazz lofi music videos daily and uploads them automatically.

**Channel:** [@midnightjazzlofi](https://youtube.com/@midnightjazzlofi)  
**Niche:** Dark lofi / lo-fi jazz — cinematic, late night, study music  
**Cost:** ~$31/month | **Upload schedule:** Daily 9am SGT

---

## How it works

Each day at 9am the pipeline runs automatically and:

1. **Generates metadata** — Claude API creates SEO-optimised title, description, and tags
2. **Generates music** — Suno API creates 20 dark jazz lofi tracks (~60 min total)
3. **Assembles audio** — FFmpeg concatenates tracks into one long MP3
4. **Generates video** — Kling AI creates a 5-sec near-static cinematic still (no-motion prompt)
5. **Assembles video** — FFmpeg loops the clip to match audio duration → final MP4
6. **Picks thumbnail** — picks oldest image from Midjourney queue, adds text overlay
7. **Uploads to YouTube** — YouTube Data API v3 uploads with all metadata

---

## Tool stack

| Tool | Purpose | Cost |
|------|---------|------|
| Suno Pro | AI music generation | $10/mo |
| Kling AI API | AI video clip generation | ~$10/mo (paid pack — tier TBD) |
| Midjourney Basic | Thumbnails (manual Sunday batch) | $10/mo |
| Claude Haiku API | SEO metadata generation | ~$0.09/mo |
| Tencent Lighthouse | VPS — Singapore region | $0.84/mo (yr1) |
| FFmpeg | Audio/video assembly | Free |
| YouTube Data API v3 | Upload automation | Free (10K units/day) |

**Total: ~$31/month**

---

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/midnight-jazz-lofi.git
cd midnight-jazz-lofi
cp .env.example .env
# Edit .env and fill in all API keys
```

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install system dependencies

```bash
sudo apt update && sudo apt install -y ffmpeg fontconfig
# Install Bebas Neue font for thumbnail overlays
mkdir -p /usr/share/fonts/truetype/bebas-neue
wget -O /tmp/BebasNeue.ttf "https://cdn.jsdelivr.net/gh/dharmatype/Bebas-Neue@master/fonts/BebasNeue(2018)ByDhamraType/ttf/BebasNeue-Regular.ttf"
sudo cp /tmp/BebasNeue.ttf /usr/share/fonts/truetype/bebas-neue/
sudo fc-cache -fv
```

### 4. YouTube OAuth setup

```bash
# Download client_secret.json from Google Cloud Console first
# Then run this once to generate token.json
python3 scripts/get_token.py
```

### 5. Add Midjourney thumbnails

Every Sunday, generate 7+ images in Midjourney using the scene prompts below.
Upload to the queue folder:

```bash
scp thumb_*.png ubuntu@YOUR_VPS:~/youtube-pipeline/thumbnails/queue/
```

### 6. Set up daily cron job

```bash
crontab -e
# Add this line:
0 9 * * * cd /home/ubuntu/youtube-pipeline && /home/ubuntu/youtube-pipeline/venv/bin/python3 -u run_pipeline.py >> /home/ubuntu/youtube-pipeline/logs/pipeline_$(date +\%Y\%m\%d).log 2>&1
```

### 7. Run manually to test

```bash
python3 -u run_pipeline.py
```

---

## Running locally as a test

The pipeline can run on your local machine (Windows / macOS / Linux) without
touching the VPS or YouTube channel. Useful for iterating on prompts, image
generation, and i2v animation without burning a 30 min round-trip.

**Test mode:** 1 mocked Suno track (FFmpeg sine tone), 1 real PiAPI Flux still,
1 real Kling i2v clip, 1 mocked Anthropic metadata, no thumbnail picking, no
YouTube upload. Cost per run: ~$0.0015 (Flux) + 10 Kling video credits.

### Local prereqs

```bash
# 1. Copy env template to repo root and fill in real keys
cp .env.example .env
# Edit .env — only PIAPI_KEY and KLING_ACCESS_KEY/KLING_SECRET_KEY are
# strictly required for a test run; the others are mocked.

# 2. Install dependencies (Python 3.11+, FFmpeg in PATH)
python3 -m venv venv
source venv/bin/activate         # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Switch to test mode

Either edit `config/pipeline.json` and change `"mode": "production"` →
`"mode": "test"`, or use the env override (preferred — no file change):

```bash
PIPELINE_MODE=test python3 -u run_pipeline.py
```

Outputs land at the repo root: `output/music/`, `output/video/`,
`output/final_audio.mp3`, `output/final_video.mp4`, `logs/pipeline_*.log`
(all gitignored).

### Cleanup

```bash
rm -rf output/ logs/
```

---

## Folder structure

```
midnight-jazz-lofi/
├── run_pipeline.py          # Master script — runs all 7 steps
├── requirements.txt
├── .env.example             # Copy to .env and fill in keys
├── .gitignore
├── scripts/
│   ├── generate_metadata.py # Claude API → title/desc/tags
│   ├── generate_music.py    # Suno API → MP3 tracks
│   ├── assemble_audio.py    # FFmpeg → concatenate tracks
│   ├── generate_video.py    # Kling API → looping scene clip
│   ├── assemble_video.py    # FFmpeg → final MP4
│   ├── pick_thumbnail.py    # MJ queue manager + text overlay
│   ├── upload_youtube.py    # YouTube Data API v3 upload
│   └── get_token.py         # One-time YouTube OAuth setup
├── thumbnails/
│   ├── queue/               # Drop Midjourney PNGs here
│   └── used/                # Pipeline moves used ones here
├── output/                  # Generated files (gitignored)
│   ├── music/               # track_01.mp3 ... track_10.mp3
│   ├── video/               # scene_X.mp4
│   ├── final_audio.mp3
│   └── final_video.mp4
└── logs/                    # Daily pipeline logs (gitignored)
```

---

## Midjourney thumbnail prompts

Use these prompts every Sunday in your private Discord MJ server.
Append `--style raw --ar 16:9 --v 7 --q 2 --s 750` to every prompt.

**Scene 1 — Rainy Tokyo**
```
dark rainy Tokyo back alley at 2am, neon signs in japanese kanji reflecting in wet cobblestone puddles, empty narrow street, orange street lamp, gentle rain streaks, cinematic film photography, deep shadows, no people
```

**Scene 2 — Jazz Bar**
```
dimly lit vintage jazz bar interior, empty wooden stage with upright piano and standing microphone, single amber spotlight, cigarette smoke wisps, dark mahogany walls, candles on empty tables, 1950s noir atmosphere, no people
```

**Scene 3 — City Rooftop**
```
dark rain-soaked rooftop overlooking vast city at night, neon lights reflecting in wet concrete, thick fog, lone empty wooden chair facing the city, film grain, atmospheric noir photography, no people
```

**Scene 4 — Late Night Cafe**
```
view from inside late night cafe looking out rain-streaked window, warm interior amber light, empty table with ceramic coffee cup, open book, blurred neon city lights through rain, cinematic depth of field, no people
```

**Scene 5 — Noir Office**
```
1940s noir detective office at midnight, single brass desk lamp, rain streaking down dark window with venetian blind shadows, whiskey glass and scattered papers on wooden desk, heavy shadows, no people
```

---

## Costs per video

| Step | Tool | Cost |
|------|------|------|
| 20 music tracks | Suno API | ~$0.04–0.48 |
| 1 video clip | Kling API | ~$0.50 |
| Metadata | Claude Haiku | ~$0.003 |
| Thumbnail | Midjourney (manual) | ~$0.33 (amortised) |
| VPS compute | Tencent Cloud | ~$0.17 |
| **Total** | | **~$1.04–1.48/video** |

---

## Monetization strategy

1. **YouTube AdSense** — primary revenue, $4–11 RPM for lofi/study niche
2. **Spotify/Apple Music** — via DistroKid ($22.99/yr), passive streaming royalties
3. **Music licensing** — Pond5/Artlist, $15–50/license
4. **Channel memberships** — available at 500 subs
5. **Affiliate links** — headphones, study apps, pinned in descriptions

**Break-even:** Projected month 8–9 at 1 video/day

---

## License

Scripts are MIT licensed. AI-generated content rights vary by provider — see Suno and Kling ToS for commercial use terms.
