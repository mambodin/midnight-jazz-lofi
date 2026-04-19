import os
import sys
import time
import jwt
import json
import base64
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

PIAPI_KEY        = os.getenv("PIAPI_KEY")
PIAPI_BASE_URL   = "https://api.piapi.ai"
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")
KLING_BASE_URL   = "https://api-singapore.klingai.com"

_config = json.loads((Path(__file__).parent.parent / "config" / "video_scenes.json").read_text())
IMAGE_API_PARAMS  = _config["image_api_params"]
VIDEO_API_PARAMS  = _config["video_api_params"]
SCENES            = _config["scenes"]
IMAGE_PROMPTS     = [s["image_prompt"] for s in SCENES]
ANIMATION_PROMPTS = [s["animation_prompt"] for s in SCENES]

# JWT cache — reuse Kling tokens while they have >60s of validity remaining
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


def kling_headers():
    return {
        "Authorization": f"Bearer {generate_jwt()}",
        "Content-Type": "application/json"
    }


def piapi_headers():
    return {
        "x-api-key": PIAPI_KEY,
        "Content-Type": "application/json"
    }


# ── Step 1: PiAPI Flux Schnell text-to-image ────────────────────────────────

def create_image_task(scene_index):
    prompt = IMAGE_PROMPTS[scene_index]
    payload = {
        "model": IMAGE_API_PARAMS["model"],
        "task_type": "txt2img",
        "input": {
            "prompt": prompt,
            "negative_prompt": IMAGE_API_PARAMS["negative_prompt"],
            "width": IMAGE_API_PARAMS["width"],
            "height": IMAGE_API_PARAMS["height"]
        }
    }

    print(f"\nSubmitting image task (scene {scene_index})...", flush=True)
    print(f"Image prompt: {prompt[:80]}...", flush=True)

    try:
        resp = requests.post(
            f"{PIAPI_BASE_URL}/api/v1/task",
            headers=piapi_headers(),
            json=payload,
            timeout=30
        )
        print(f"HTTP {resp.status_code}", flush=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Image request error: {e}", flush=True)
        return None

    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        print(f"No task_id in PiAPI response: {data}", flush=True)
        return None

    print(f"image task_id: {task_id}", flush=True)
    return task_id


def poll_image_task(task_id, max_attempts=60, interval=10):
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{PIAPI_BASE_URL}/api/v1/task/{task_id}",
                headers=piapi_headers(),
                timeout=15
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                print(f"Image poll {attempt} — rate limited, waiting {retry_after}s", flush=True)
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Image poll {attempt} error: {e}", flush=True)
            continue

        status = data.get("data", {}).get("status", "Unknown")
        print(f"Image poll {attempt}/{max_attempts} — {status}", flush=True)

        if status == "Completed":
            return data["data"]
        if status == "Failed":
            print(f"Image task failed: {data}", flush=True)
            return None

    print("Image polling timed out", flush=True)
    return None


def download_image(url, out_path):
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        size_mb = len(resp.content) / (1024 * 1024)
        print(f"Downloaded {out_path.name} ({size_mb:.2f} MB)", flush=True)
        return True
    except Exception as e:
        print(f"Image download error: {e}", flush=True)
        return False


# ── Step 4: Kling direct image-to-video ──────────────────────────────────────

def create_video_task(scene_index, image_path):
    prompt = ANIMATION_PROMPTS[scene_index]

    try:
        image_bytes = Path(image_path).read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
    except Exception as e:
        print(f"Failed to encode image: {e}", flush=True)
        return None

    payload = {**VIDEO_API_PARAMS, "prompt": prompt, "image": image_b64}

    print(f"\nSubmitting video task (scene {scene_index})...", flush=True)
    print(f"Animation prompt: {prompt[:80]}...", flush=True)

    try:
        resp = requests.post(
            f"{KLING_BASE_URL}/v1/videos/image2video",
            headers=kling_headers(),
            json=payload,
            timeout=30
        )
        print(f"HTTP {resp.status_code}", flush=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Video request error: {e}", flush=True)
        return None

    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        print(f"No task_id in Kling response: {data}", flush=True)
        return None

    print(f"video task_id: {task_id}", flush=True)
    return task_id


def poll_video_task(task_id, max_attempts=60, interval=10):
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        try:
            resp = requests.get(
                f"{KLING_BASE_URL}/v1/videos/image2video/{task_id}",
                headers=kling_headers(),
                timeout=15
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                print(f"Video poll {attempt} — rate limited, waiting {retry_after}s", flush=True)
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Video poll {attempt} error: {e}", flush=True)
            continue

        task_status = data.get("data", {}).get("task_status", "UNKNOWN")
        print(f"Video poll {attempt}/{max_attempts} — {task_status}", flush=True)

        if task_status == "succeed":
            return data["data"]
        if task_status in ("failed", "error"):
            print(f"Video task failed: {data}", flush=True)
            return None

    print("Video polling timed out", flush=True)
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
        print(f"Video download error: {e}", flush=True)
        return False


# ── Orchestration ────────────────────────────────────────────────────────────

def generate_video(scene_index, output_dir="output/video"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Remove any stale artifacts from a previous failed run
    video_path = out / f"scene_{scene_index}.mp4"
    image_path = out / f"scene_{scene_index}_still.png"
    if video_path.exists():
        video_path.unlink()
        print(f"Removed stale clip: {video_path.name}", flush=True)
    if image_path.exists():
        image_path.unlink()
        print(f"Removed stale still: {image_path.name}", flush=True)

    # Step 1: image task on PiAPI
    image_task_id = create_image_task(scene_index)
    if not image_task_id:
        return None

    # Step 2: poll PiAPI image task
    print("Polling for image completion...", flush=True)
    image_result = poll_image_task(image_task_id)
    if not image_result:
        return None

    image_url = image_result.get("output", {}).get("image_url")
    if not image_url:
        print(f"No image_url in result: {image_result}", flush=True)
        return None

    # Step 3: download still
    print("Downloading still image...", flush=True)
    if not download_image(image_url, image_path):
        return None

    # Step 4: i2v task on Kling direct
    video_task_id = create_video_task(scene_index, image_path)
    if not video_task_id:
        return None

    # Step 5: poll Kling video task
    print("Polling for video completion...", flush=True)
    video_result = poll_video_task(video_task_id)
    if not video_result:
        return None

    videos = video_result.get("task_result", {}).get("videos", [])
    if not videos:
        print(f"No videos in result: {video_result}", flush=True)
        return None

    video_url = videos[0].get("url")
    if not video_url:
        print(f"No URL in video: {videos[0]}", flush=True)
        return None

    # Step 6: download video
    print("Downloading video...", flush=True)
    if download_video(video_url, video_path):
        return str(video_path)
    return None


if __name__ == "__main__":
    scene_idx = random.randint(0, 4)
    print(f"Generating video — scene {scene_idx}", flush=True)
    path = generate_video(scene_index=scene_idx)
    if path:
        print(f"\nSuccess! Video saved: {path}", flush=True)
    else:
        print("\nFailed — check errors above", flush=True)
