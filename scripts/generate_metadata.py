import os
import re
import json
import time
import anthropic
from dotenv import load_dotenv

from pipeline_config import ENV_PATH, MOCK_METADATA

load_dotenv(dotenv_path=ENV_PATH)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MOODS = [
    "slow dark jazz lofi, brushed drums, upright bass, muted trumpet, 70bpm melancholic",
    "rainy night beats, lo-fi hip-hop, vinyl crackle, soft piano, distant saxophone",
    "cinematic noir jazz, brooding double bass, sparse guitar, 65bpm atmospheric",
    "smooth dark jazz lofi, mid-tempo 90bpm, clean guitar, light percussion",
    "winter jazz lofi, cold sparse piano, 72bpm minor key, distant strings"
]

SCENES = [
    "rainy Tokyo alley at night, neon reflections in wet cobblestones",
    "dimly lit jazz bar interior, amber spotlight, cigarette smoke, empty stage",
    "city rooftop at night, rain, neon glow below, fog, lone empty chair",
    "late night cafe, rain on window, coffee cup, open book, blurred city lights",
    "noir detective office, desk lamp, venetian blinds, whiskey glass, city rain outside"
]

REQUIRED_KEYS = {"title", "short_title", "scene_label", "description", "tags", "category_id"}

# Fallback metadata when the API call fails after all retries
_FALLBACK_MOOD_LABELS  = ["Dark Jazz Lofi", "Rainy Night Lofi", "Noir Jazz", "Smooth Dark Jazz", "Winter Jazz Lofi"]
_FALLBACK_SCENE_LABELS = ["RAINY TOKYO", "JAZZ BAR NIGHT", "CITY ROOFTOP", "LATE NIGHT CAFE", "NOIR OFFICE"]
_FALLBACK_SHORT_TITLES = ["JAZZ LOFI", "RAINY LOFI", "NOIR JAZZ", "SMOOTH JAZZ", "WINTER JAZZ"]
_FALLBACK_TAGS = [
    "lofi jazz", "dark lofi", "study music", "focus music",
    "jazz lofi", "late night music", "instrumental jazz",
    "lofi hip hop", "chill beats", "midnight vibes",
    "rainy night music", "coding music"
]


def _extract_json(raw):
    """Strip markdown code fences and return cleaned JSON string."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split('\n')
        # Drop opening fence line (```json, ```JSON, ``` etc.)
        lines = lines[1:]
        # Drop closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = '\n'.join(lines)
    return raw.strip()


def _validate_meta(meta, duration_mins):
    """Validate required keys and types. Truncates overlong drawtext strings."""
    missing = REQUIRED_KEYS - set(meta.keys())
    if missing:
        raise ValueError(f"Missing keys in model response: {missing}")
    if not isinstance(meta["tags"], list) or len(meta["tags"]) == 0:
        raise ValueError("tags must be a non-empty list")
    # Clamp drawtext fields to 25 chars so they fit the 1280×720 canvas
    meta["short_title"] = str(meta["short_title"])[:25].upper()
    meta["scene_label"] = str(meta["scene_label"])[:25].upper()
    return meta


def _build_fallback(mood_index, scene_index, duration_mins):
    mood_label  = _FALLBACK_MOOD_LABELS[mood_index]
    scene_label = _FALLBACK_SCENE_LABELS[scene_index]
    return {
        "title": f"{duration_mins} Min {mood_label} | {scene_label.title()} — Study & Focus Music",
        "short_title": _FALLBACK_SHORT_TITLES[mood_index],
        "scene_label": scene_label,
        "description": (
            f"{mood_label} beats for studying, coding, and deep focus. "
            f"Atmospheric late-night vibes with cinematic piano and bass. "
            f"New videos daily. Subscribe for more."
        ),
        "tags": _FALLBACK_TAGS,
        "category_id": "10"
    }


def generate_metadata(mood_index, scene_index, duration_mins=90, max_retries=3):
    if MOCK_METADATA:
        print("  Metadata mocked (test mode) — using fallback template", flush=True)
        return _build_fallback(mood_index, scene_index, duration_mins)

    mood  = MOODS[mood_index]
    scene = SCENES[scene_index]

    prompt = f"""You are a YouTube SEO specialist for a dark jazz lofi music channel called "Midnight Jazz Lofi".

Generate metadata for a new upload with this profile:
- Music mood: {mood}
- Visual scene: {scene}
- Video duration: {duration_mins} minutes
- Channel niche: dark lofi jazz, cinematic, late night focus music

Return ONLY valid JSON with exactly these keys, no markdown, no explanation:
{{
  "title": "max 70 chars, format: [Duration] [mood description] | [visual vibe]",
  "short_title": "max 20 chars uppercase, e.g. 2 HRS LOFI JAZZ",
  "scene_label": "max 20 chars uppercase, e.g. RAINY TOKYO NIGHT",
  "description": "3 sentences max 500 chars total, describe mood and use case, end with: New videos daily. Subscribe for more.",
  "tags": ["exactly 12 tags mixing broad and niche keywords"],
  "category_id": "10"
}}"""

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            raw     = message.content[0].text.strip()
            cleaned = _extract_json(raw)
            meta    = json.loads(cleaned)
            return _validate_meta(meta, duration_mins)
        except Exception as e:
            last_err = e
            print(f"  Metadata attempt {attempt}/{max_retries} failed: {e}", flush=True)
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    print(f"  All {max_retries} metadata attempts failed ({last_err}). Using fallback template.", flush=True)
    return _build_fallback(mood_index, scene_index, duration_mins)


if __name__ == "__main__":
    import random
    mood_idx  = random.randint(0, 4)
    scene_idx = random.randint(0, 4)
    print(f"Mood: {mood_idx}, Scene: {scene_idx}\n")
    result = generate_metadata(mood_idx, scene_idx, duration_mins=90)
    print(json.dumps(result, indent=2))
