import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser('~/youtube-pipeline/.env'))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

TOKEN_PATH  = os.path.expanduser('~/youtube-pipeline/token.json')
SECRET_PATH = os.getenv(
    'YOUTUBE_CLIENT_SECRET_PATH',
    os.path.expanduser('~/youtube-pipeline/client_secret.json')
)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]


def _save_token(creds):
    """Write token atomically with restricted permissions."""
    tmp = TOKEN_PATH + ".tmp"
    with open(tmp, 'w') as f:
        f.write(creds.to_json())
    os.replace(tmp, TOKEN_PATH)
    os.chmod(TOKEN_PATH, 0o600)


def get_youtube_client():
    if not Path(TOKEN_PATH).exists():
        print(f"ERROR: token.json not found at {TOKEN_PATH}", flush=True)
        print("Run get_token.py first", flush=True)
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("Refreshing OAuth token...", flush=True)
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"ERROR: OAuth token refresh failed: {e}", flush=True)
                print("Re-run get_token.py to generate a new token.", flush=True)
                sys.exit(1)
            _save_token(creds)
        else:
            print("ERROR: OAuth credentials are invalid and cannot be refreshed.", flush=True)
            print("Re-run get_token.py to generate a new token.", flush=True)
            sys.exit(1)

    return build('youtube', 'v3', credentials=creds)


def upload_video(
    video_path,
    title,
    description,
    tags,
    thumbnail_path=None,
    category_id="10",
    privacy="public"
):
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"\nUploading to YouTube...", flush=True)
    print(f"File:    {video_path.name} ({size_mb:.0f} MB)", flush=True)
    print(f"Title:   {title}", flush=True)
    print(f"Privacy: {privacy}", flush=True)

    youtube = get_youtube_client()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": "en"
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  Upload progress: {pct}%", flush=True)
        except HttpError as e:
            print(f"  Upload error: {e}", flush=True)
            raise

    video_id = response.get("id")
    print(f"\nUpload complete!", flush=True)
    print(f"Video ID:  {video_id}", flush=True)
    print(f"Video URL: https://www.youtube.com/watch?v={video_id}", flush=True)

    if thumbnail_path and Path(thumbnail_path).exists():
        print(f"\nSetting thumbnail...", flush=True)
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path))
            ).execute()
            print("Thumbnail set successfully", flush=True)
        except HttpError as e:
            print(f"Thumbnail error (non-fatal): {e}", flush=True)

    return video_id


if __name__ == "__main__":
    video = "output/final_video.mp4"
    thumb = "thumbnails/queue/thumb_001.png"

    title = "90 Min Dark Jazz Lofi | Rainy Tokyo Night — Study & Focus Music"
    description = """Slow dark jazz lofi with brushed drums, upright bass, and muted trumpet for late-night studying and deep focus sessions. Perfect for coding, writing, and unwinding to cinematic rain ambience.

New videos uploaded daily. Subscribe for more midnight jazz lofi.

#lofi #jazzlofi #darklofi #studymusic #focusmusic #lofijazz #chillbeats #midnightvibes #latenight #instrumentalmusic"""

    tags = [
        "lofi jazz", "dark lofi", "study music", "focus music",
        "jazz lofi", "late night music", "instrumental jazz",
        "lofi hip hop", "chill beats", "midnight vibes",
        "rainy night music", "coding music"
    ]

    if not Path(video).exists():
        print(f"ERROR: {video} not found. Run assemble_video.py first.")
        sys.exit(1)

    thumb_path = thumb if Path(thumb).exists() else None
    if not thumb_path:
        print("No thumbnail found — uploading without thumbnail", flush=True)

    video_id = upload_video(
        video_path=video,
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=thumb_path,
        privacy="private"
    )

    print(f"\nDone! Check YouTube Studio:")
    print(f"https://studio.youtube.com/video/{video_id}/edit")
