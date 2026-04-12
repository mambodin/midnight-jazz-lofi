import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

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


def generate_metadata(mood_index, scene_index, duration_mins=90):
    mood = MOODS[mood_index]
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

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


if __name__ == "__main__":
    import random
    mood_idx = random.randint(0, 4)
    scene_idx = random.randint(0, 4)
    print(f"Mood: {mood_idx}, Scene: {scene_idx}\n")
    result = generate_metadata(mood_idx, scene_idx, duration_mins=90)
    print(json.dumps(result, indent=2))
