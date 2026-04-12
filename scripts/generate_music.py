import os
import time
import json
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

SUNO_API_KEY      = os.getenv("SUNO_API_KEY")
SUNO_CALLBACK_URL = os.getenv("SUNO_CALLBACK_URL")
BASE_URL          = "https://api.sunoapi.org/api/v1"

HEADERS = {
    "Authorization": f"Bearer {SUNO_API_KEY}",
    "Content-Type": "application/json"
}

MUSIC_STYLES = [
    {
        "style": "Dark Jazz, Lo-Fi",
        "prompt": "slow dark jazz lofi, brushed snare drums, upright bass, muted trumpet melody, melancholic minor key, vinyl crackle, late night atmosphere, 70bpm",
        "negativeTags": "upbeat, happy, vocals, singing, pop, electronic, EDM"
    },
    {
        "style": "Lo-Fi Hip Hop, Jazz",
        "prompt": "rainy night lofi hip-hop jazz, soft piano chords, distant saxophone, vinyl crackle, light rain ambience, 80bpm, melancholic focused mood, warm low-fi production",
        "negativeTags": "upbeat, fast tempo, vocals, singing, heavy drums, EDM"
    },
    {
        "style": "Cinematic Jazz, Noir",
        "prompt": "cinematic noir jazz instrumental, brooding double bass, sparse electric guitar, atmospheric piano, slow 65bpm, minor key, 1950s detective film score mood, smoky and dark",
        "negativeTags": "upbeat, vocals, singing, pop, electronic, fast tempo"
    },
    {
        "style": "Smooth Jazz, Lo-Fi",
        "prompt": "smooth dark jazz lofi, mid-tempo 90bpm, clean guitar chords, soft upright bass, light percussion brushwork, focused productive mood, dark but not sad, lo-fi texture",
        "negativeTags": "sad, depressing, vocals, singing, heavy bass, EDM, pop"
    },
    {
        "style": "Winter Jazz, Lo-Fi",
        "prompt": "winter lofi jazz, cold sparse piano, slow 72bpm, minor key, distant string pads, melancholic mood, snow and silence atmosphere, lo-fi vinyl texture, introspective",
        "negativeTags": "upbeat, happy, vocals, singing, summer, tropical, EDM"
    }
]

COMPLETE_STATUSES = {"SUCCESS"}
FAILED_STATUSES   = {"FAILED", "ERROR", "REJECTED"}


def poll_until_complete(task_id, max_attempts=60, interval=10):
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{BASE_URL}/generate/record-info",
                headers=HEADERS,
                params={"taskId": task_id},
                timeout=15
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            print(f"    Poll {attempt}/{max_attempts} error: {e}", flush=True)
            continue

        status = body.get("data", {}).get("status", "UNKNOWN")
        print(f"    Poll {attempt}/{max_attempts} — {status}", flush=True)

        if status in COMPLETE_STATUSES:
            return body["data"]
        if status in FAILED_STATUSES:
            print(f"    Generation failed: {body}", flush=True)
            return None

    print("    Timed out waiting for completion", flush=True)
    return None


def download_audio(url, out_path):
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        size_kb = len(resp.content) // 1024
        print(f"    Downloaded {out_path.name} ({size_kb} KB)", flush=True)
        return True
    except Exception as e:
        print(f"    Download failed: {e}", flush=True)
        return False


def generate_track(style_index, track_num, output_dir):
    style = MUSIC_STYLES[style_index]
    title = f"Midnight Jazz Lofi - Track {track_num:02d}"

    payload = {
        "customMode": True,
        "instrumental": True,
        "model": "V4_5ALL",
        "prompt": style["prompt"],
        "style": style["style"],
        "title": title,
        "negativeTags": style["negativeTags"],
        "styleWeight": 0.7,
        "weirdnessConstraint": 0.3,
        "callBackUrl": SUNO_CALLBACK_URL
    }

    print(f"\n  Track {track_num} — requesting ({style['style']})...", flush=True)

    try:
        resp = requests.post(
            f"{BASE_URL}/generate",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Request error: {e}", flush=True)
        return None

    task_id = data.get("data", {}).get("taskId")
    if not task_id:
        print(f"  No taskId in response: {data}", flush=True)
        return None

    print(f"  taskId: {task_id} — waiting...", flush=True)
    result = poll_until_complete(task_id)
    if not result:
        return None

    suno_data = result.get("response", {}).get("sunoData", [])
    if not suno_data:
        print(f"  No sunoData in result", flush=True)
        return None

    clip = suno_data[0]
    audio_url = clip.get("sourceAudioUrl") or clip.get("audioUrl")
    duration  = clip.get("duration", 0)

    if not audio_url:
        print(f"  No audio URL found", flush=True)
        return None

    print(f"  Duration: {duration:.1f}s — downloading...", flush=True)
    out_path = output_dir / f"track_{track_num:02d}.mp3"

    if download_audio(audio_url, out_path):
        return str(out_path)
    return None


def generate_music_batch(style_index, num_tracks=8, output_dir="output/music"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {num_tracks} track(s)", flush=True)
    print(f"Style: {MUSIC_STYLES[style_index]['style']}", flush=True)
    print(f"Output: {out}\n", flush=True)

    tracks = []
    for i in range(1, num_tracks + 1):
        path = generate_track(style_index, i, out)
        if path:
            tracks.append(path)
        else:
            print(f"  Track {i} failed — continuing", flush=True)
        if i < num_tracks:
            time.sleep(3)

    print(f"\nDone: {len(tracks)}/{num_tracks} tracks saved", flush=True)
    for t in tracks:
        print(f"  {t}", flush=True)
    return tracks


if __name__ == "__main__":
    style_idx = random.randint(0, 4)
    print(f"Style index: {style_idx} — {MUSIC_STYLES[style_idx]['style']}")
    generate_music_batch(style_index=style_idx, num_tracks=1)
