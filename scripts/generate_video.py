import os
import sys
import time
import jwt
import json
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")
BASE_URL         = "https://api-singapore.klingai.com"

_config = json.loads((Path(__file__).parent.parent / "config" / "video_scenes.json").read_text())
API_PARAMS = _config["api_params"]
SCENES = _config["scenes"]
SCENE_PROMPTS = [s["prompt"] for s in SCENES]

# JWT cache — reuse tokens while they have >60s of validity remaining
_jwt_cache = {"token": None, "exp": 0}


def generate_jwt():
    now = int(time.time())
    if _jwt_cache["token"] and _jwt_cache["exp"] - now > 60:
        return _jwt_cache["token"]
    exp = now + 1800
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": exp,
        "nbf": now - 5
    }
    token = jwt.encode(
        payload, KLING_SECRET_KEY,
        algorithm="HS256",
        headers={"alg": "HS256", "typ": "JWT"}
    )
    _jwt_cache["token"] = token
    _jwt_cache["exp"]   = exp
    return token


def get_headers():
    return {
        "Authorization": f"Bearer {generate_jwt()}",
        "Content-Type": "application/json"
    }


def create_video_task(scene_index):
    prompt = SCENE_PROMPTS[scene_index]
    payload = {**API_PARAMS, "prompt": prompt}

    print(f"\nSubmitting video task (scene {scene_index})...", flush=True)
    print(f"Prompt: {prompt[:80]}...", flush=True)

    try:
        resp = requests.post(
            f"{BASE_URL}/v1/videos/text2video",
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        print(f"HTTP {resp.status_code}", flush=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Request error: {e}", flush=True)
        return None

    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        print(f"No task_id in response: {data}", flush=True)
        return None

    print(f"task_id: {task_id}", flush=True)
    return task_id


def poll_video_task(task_id, max_attempts=60, interval=10):
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{BASE_URL}/v1/videos/text2video/{task_id}",
                headers=get_headers(),
                timeout=15
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                print(f"Poll {attempt} — rate limited, waiting {retry_after}s", flush=True)
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Poll {attempt} error: {e}", flush=True)
            continue

        task_status = data.get("data", {}).get("task_status", "UNKNOWN")
        print(f"Poll {attempt}/{max_attempts} — {task_status}", flush=True)

        if task_status == "succeed":
            return data["data"]
        if task_status in ("failed", "error"):
            print(f"Task failed: {data}", flush=True)
            return None

    print("Timed out", flush=True)
    return None


def download_video(url, out_path):
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        size_mb = len(resp.content) / (1024 * 1024)
        print(f"Downloaded {out_path.name} ({size_mb:.1f} MB)", flush=True)
        return True
    except Exception as e:
        print(f"Download error: {e}", flush=True)
        return False


def generate_video(scene_index, output_dir="output/video"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Remove any stale clip from a previous failed run so we don't silently reuse it
    out_path = out / f"scene_{scene_index}.mp4"
    if out_path.exists():
        out_path.unlink()
        print(f"Removed stale clip: {out_path.name}", flush=True)

    task_id = create_video_task(scene_index)
    if not task_id:
        return None

    print("Polling for completion...", flush=True)
    result = poll_video_task(task_id)
    if not result:
        return None

    videos = result.get("task_result", {}).get("videos", [])
    if not videos:
        print(f"No videos in result: {result}", flush=True)
        return None

    video_url = videos[0].get("url")
    if not video_url:
        print(f"No URL in video: {videos[0]}", flush=True)
        return None

    print("Downloading video...", flush=True)
    if download_video(video_url, out_path):
        return str(out_path)
    return None


if __name__ == "__main__":
    scene_idx = random.randint(0, 4)
    print(f"Generating video — scene {scene_idx}", flush=True)
    path = generate_video(scene_index=scene_idx)
    if path:
        print(f"\nSuccess! Video saved: {path}", flush=True)
    else:
        print("\nFailed — check errors above", flush=True)
