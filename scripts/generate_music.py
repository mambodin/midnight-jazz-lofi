import os
import time
import json
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_CALLBACK_URL = os.getenv("SUNO_CALLBACK_URL")
BASE_URL = "https://api.sunoapi.org/api/v1"

HEADERS = {
    "Authorization": f"Bearer {SUNO_API_KEY}",
    "Content-Type": "application/json"
}

_config = json.loads((Path(__file__).parent.parent / "config" / "music_styles.json").read_text())
MUSIC_STYLES = _config["styles"]
_api_params = _config["api_params"]

COMPLETE_STATUSES = {"SUCCESS"}
FAILED_STATUSES  = {"FAILED", "ERROR", "REJECTED"}


def poll_until_complete(task_id: str, max_attempts: int = 60, interval: int = 10):
    """Poll record-info until SUCCESS or failure. Returns data dict or None."""
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{BASE_URL}/generate/record-info",
                headers=HEADERS,
                params={"taskId": task_id},
                timeout=15
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                print(f"    Poll {attempt} — rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            print(f"    Poll {attempt}/{max_attempts} error: {e}")
            continue

        status = body.get("data", {}).get("status", "UNKNOWN")
        print(f"    Poll {attempt}/{max_attempts} — {status}")

        if status in COMPLETE_STATUSES:
            return body["data"]
        if status in FAILED_STATUSES:
            print(f"    Generation failed: {body}")
            return None

    print("    Timed out waiting for completion")
    return None


def download_audio(url: str, out_path: Path) -> bool:
    """Download MP3 from URL to out_path. Returns True on success."""
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        size_kb = len(resp.content) // 1024
        print(f"    Downloaded {out_path.name} ({size_kb} KB)")
        return True
    except Exception as e:
        print(f"    Download failed: {e}")
        return False


def generate_track(style_index: int, track_num: int, output_dir: Path) -> str | None:
    """Generate one track, poll until done, download it. Returns file path or None."""
    style = MUSIC_STYLES[style_index]
    title = f"Midnight Jazz Lofi - Track {track_num:02d}"

    payload = {
        "customMode": True,
        "instrumental": _api_params["instrumental"],
        "model": _api_params["model"],
        "prompt": style["prompt"],
        "style": style["style"],
        "title": title,
        "negativeTags": style["negativeTags"],
        "styleWeight": _api_params["styleWeight"],
        "weirdnessConstraint": _api_params["weirdnessConstraint"],
        "callBackUrl": SUNO_CALLBACK_URL
    }

    print(f"\n  Track {track_num} — requesting ({style['style']})...")

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
        print(f"  Request error: {e}")
        return None

    task_id = data.get("data", {}).get("taskId")
    if not task_id:
        print(f"  No taskId in response: {data}")
        return None

    print(f"  taskId: {task_id} — waiting for completion...")
    result = poll_until_complete(task_id)

    if not result:
        return None

    # Extract audio URL from sunoData[0]
    suno_data = result.get("response", {}).get("sunoData", [])
    if not suno_data:
        print(f"  No sunoData in result: {result}")
        return None

    # Use sourceAudioUrl (direct CDN) with audioUrl as fallback
    clip = suno_data[0]
    audio_url = clip.get("sourceAudioUrl") or clip.get("audioUrl")
    duration  = float(clip.get("duration", 0))

    if not audio_url:
        print(f"  No audio URL found in clip: {clip}")
        return None

    if duration < 60:
        print(f"  Track too short ({duration:.1f}s < 60s) — skipping stub")
        return None

    print(f"  Duration: {duration:.1f}s — downloading...")
    out_path = output_dir / f"track_{track_num:02d}.mp3"

    if download_audio(audio_url, out_path):
        return str(out_path)
    return None


def generate_music_batch(style_index: int, num_tracks: int = 8,
                         output_dir: str = "output/music") -> list:
    """Generate a full batch of tracks. Returns list of file paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {num_tracks} track(s)")
    print(f"Style: {MUSIC_STYLES[style_index]['style']}")
    print(f"Output: {out}\n")

    tracks = []
    for i in range(1, num_tracks + 1):
        path = generate_track(style_index, i, out)
        if path:
            tracks.append(path)
        else:
            print(f"  Track {i} failed — continuing")
        if i < num_tracks:
            time.sleep(3)

    print(f"\nDone: {len(tracks)}/{num_tracks} tracks saved")
    for t in tracks:
        print(f"  {t}")
    return tracks


if __name__ == "__main__":
    style_idx = random.randint(0, 4)
    print(f"Style index: {style_idx} — {MUSIC_STYLES[style_idx]['style']}")
    generate_music_batch(style_index=style_idx, num_tracks=1)
