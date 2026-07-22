"""
Stage 7: Posting (runs only after Telegram approval).

Uses the official, free YouTube Data API v3 and Instagram Graph API.
Both require one-time account setup (see README) but no ongoing cost.
"""
import json
import os
import time

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = "youtube_token.json"


def get_youtube_client():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, YOUTUBE_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            msg = (
                "⚠️ YouTube authorization expired or failed. "
                "Run `python post_social.py` locally to re-authorize, then update "
                f"the YOUTUBE_TOKEN_JSON secret. Error: {e}"
            )
            print(f"::error::{msg}")
            raise RuntimeError(msg)
    if not creds or not creds.valid:
        # Browser authorization must be completed locally first. GitHub Actions
        # restores the resulting refresh-token JSON from a repository secret.
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise RuntimeError(
                "YouTube authorization is unavailable. Create YOUTUBE_TOKEN_JSON "
                "from a successful local authorization and save it as a GitHub secret."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def post_youtube(video_path: str, title: str, description: str, tags: list, privacy_status: str = "public", thumbnail_path: str = None):
    youtube = get_youtube_client()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
    print(f"YouTube upload complete: https://youtu.be/{response['id']}")
    
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            print(f"Uploading thumbnail from {thumbnail_path}...")
            youtube.thumbnails().set(
                videoId=response["id"],
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("Thumbnail uploaded successfully.")
        except Exception as e:
            print(f"Warning: Failed to upload thumbnail (is your channel phone-verified?): {e}")

    return response["id"]


def post_instagram(video_path: str, caption: str):
    """
    Two-step Graph API flow: create a media container from a publicly
    reachable video URL, then publish it. Since Actions runners don't have
    a stable public URL, we upload the file to a short-lived host first —
    here we use the video's GitHub Release asset URL (already public).
    """
    ig_user_id = os.environ["IG_BUSINESS_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    video_url = os.environ["RELEASE_VIDEO_URL"]  # public URL, passed in by the workflow

    import subprocess
    draft_id = os.environ.get("DRAFT_ID", "")

    # For IG Graph API to work, the video URL must be public.
    # GitHub Draft Release assets are NOT public. We must publish it temporarily.
    if draft_id:
        print("Publishing release temporarily for Instagram Graph API...")
        subprocess.run(["gh", "release", "edit", draft_id, "--draft=false"], check=True)
        time.sleep(2) # Give GitHub CDN a moment

    try:
        create_resp = requests.post(
            f"https://graph.facebook.com/v25.0/{ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": access_token,
            },
            timeout=60,
        )
        create_resp.raise_for_status()
        container_id = create_resp.json()["id"]

        # Poll until the container finishes processing
        for _ in range(30):
            status_resp = requests.get(
                f"https://graph.facebook.com/v25.0/{container_id}",
                params={"fields": "status_code", "access_token": access_token},
                timeout=30,
            )
            status = status_resp.json().get("status_code")
            if status == "FINISHED":
                break
            if status in {"ERROR", "EXPIRED"}:
                raise RuntimeError(f"Instagram processing failed: {status_resp.text}")
            time.sleep(10)
        else:
            raise TimeoutError("Instagram did not finish processing within five minutes")

        publish_resp = requests.post(
            f"https://graph.facebook.com/v25.0/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": access_token},
            timeout=60,
        )
        publish_resp.raise_for_status()
        print(f"Instagram Reel published: {publish_resp.json()}")
    finally:
        if draft_id:
            print("Re-drafting release...")
            subprocess.run(["gh", "release", "edit", draft_id, "--draft=true"], check=False)


if __name__ == "__main__":
    video_path = os.environ.get("VIDEO_PATH", "output/final.mp4")
    script_path = os.environ.get("SCRIPT_PATH", "output/script.json")
    with open(script_path) as f:
        meta = json.load(f)

    description = meta["script"] + "\n\n" + " ".join(meta["hashtags"])

    thumbnail_path = os.environ.get("THUMBNAIL_PATH")
    video_id = post_youtube(
        video_path,
        meta["caption_title"],
        description,
        [h.strip("#") for h in meta["hashtags"]],
        os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
        thumbnail_path
    )
    if os.environ.get("POST_INSTAGRAM", "false").lower() == "true":
        post_instagram(video_path, description)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"youtube_url=https://youtu.be/{video_id}\n")
