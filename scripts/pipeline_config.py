"""Shared pipeline config — mode toggle (production vs test) for run paths and behavior.

Loads `config/pipeline.json` from the repo root, applies env-var overrides, and
exposes module-level constants that the rest of the pipeline imports.

Env overrides (all optional):
  PIPELINE_MODE    — overrides the JSON `mode` field ("production" | "test")
  NUM_TRACKS       — overrides the active mode's num_tracks
  VIDEO_PRIVACY    — overrides the active mode's video_privacy
  SKIP_UPLOAD      — "true"/"false"
  SKIP_THUMBNAIL   — "true"/"false"
  MOCK_MUSIC       — "true"/"false"
  MOCK_METADATA    — "true"/"false"
"""
import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_config = json.loads((REPO_ROOT / "config" / "pipeline.json").read_text())

MODE = os.getenv("PIPELINE_MODE", _config["mode"])
if MODE not in _config["modes"]:
    raise RuntimeError(
        f"Unknown PIPELINE_MODE {MODE!r} — must be one of {list(_config['modes'])}"
    )

_active = _config["modes"][MODE]


def _resolve_base_dir(value):
    if value == ".":
        return REPO_ROOT
    if value.startswith("~"):
        return Path(os.path.expanduser(value))
    return Path(value)


def _bool_env(name, default):
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


BASE_DIR       = _resolve_base_dir(_active["base_dir"])
ENV_PATH       = BASE_DIR / ".env"
OUTPUT_DIR     = BASE_DIR / "output"
LOG_DIR        = BASE_DIR / "logs"
NUM_TRACKS     = int(os.getenv("NUM_TRACKS", _active["num_tracks"]))
VIDEO_PRIVACY  = os.getenv("VIDEO_PRIVACY", _active["video_privacy"])
SKIP_UPLOAD    = _bool_env("SKIP_UPLOAD", _active["skip_upload"])
SKIP_THUMBNAIL = _bool_env("SKIP_THUMBNAIL", _active["skip_thumbnail"])
MOCK_MUSIC     = _bool_env("MOCK_MUSIC", _active["mock_music"])
MOCK_METADATA  = _bool_env("MOCK_METADATA", _active["mock_metadata"])


if __name__ == "__main__":
    print(f"MODE:           {MODE}")
    print(f"BASE_DIR:       {BASE_DIR}")
    print(f"ENV_PATH:       {ENV_PATH}")
    print(f"OUTPUT_DIR:     {OUTPUT_DIR}")
    print(f"LOG_DIR:        {LOG_DIR}")
    print(f"NUM_TRACKS:     {NUM_TRACKS}")
    print(f"VIDEO_PRIVACY:  {VIDEO_PRIVACY}")
    print(f"SKIP_UPLOAD:    {SKIP_UPLOAD}")
    print(f"SKIP_THUMBNAIL: {SKIP_THUMBNAIL}")
    print(f"MOCK_MUSIC:     {MOCK_MUSIC}")
    print(f"MOCK_METADATA:  {MOCK_METADATA}")
