"""
Stage 7: Posting (runs only after Telegram approval).

Uses the official, free YouTube Data API v3 and Instagram Graph API.
Both require one-time account setup (see README) but no ongoing cost.
"""
import json
import os
import time

import requests
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
    if not creds or not creds.valid:
        # First-time local auth only — in CI, TOKEN_PATH is restored from a
        # GitHub Secret set up once during initial local testing.
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def post_youtube(video_path: str, title: str, description: str, tags: list, privacy_status: str = "public"):
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

    create_resp = requests.post(
        f"https://graph.facebook.com/v21.0/{ig_user_id}/media",
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
            f"https://graph.facebook.com/v21.0/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        status = status_resp.json().get("status_code")
        if status == "FINISHED":
            break
        time.sleep(10)

    publish_resp = requests.post(
        f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=60,
    )
    publish_resp.raise_for_status()
    print(f"Instagram Reel published: {publish_resp.json()}")


if __name__ == "__main__":
    with open("output/approved/script.json") as f:
        meta = json.load(f)

    description = meta["script"] + "\n\n" + " ".join(meta["hashtags"])

    post_youtube(
        "output/approved/final.mp4",
        meta["caption_title"],
        description,
        [h.strip("#") for h in meta["hashtags"]],
    )
    post_instagram("output/approved/final.mp4", description)
