"""
Stage 5: Review gate.

Sends the assembled draft video to your Telegram with inline Approve/Reject
buttons. This is the ONE manual step in the whole pipeline, done from your
phone in a few seconds.

The draft itself is stored as a GitHub Release asset (free, persists across
workflow runs) tagged with a unique draft_id. The Telegram button encodes
that draft_id, so the check_approvals workflow later knows exactly which
release to act on.
"""
import json
import os
import sys

import requests

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_for_review(draft_id: str, video_path: str, title: str, hashtags: list):
    caption = f"🎬 *{title}*\n\n{' '.join(hashtags)}\n\nApprove to post this YouTube Short?"
    
    reply_markup = json.dumps({
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{draft_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{draft_id}"},
            ]
        ]
    })

    if os.path.exists(video_path):
        with open(video_path, "rb") as video_file:
            resp = requests.post(
                f"{API}/sendVideo",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": reply_markup,
                },
                files={"video": video_file},
                timeout=120,
            )
        try:
            resp.raise_for_status()
            print(f"Sent draft {draft_id} for review with video.")
            return
        except requests.exceptions.HTTPError as e:
            print(f"Failed to send video, falling back to text. Error: {e}")
    else:
        print(f"Video {video_path} not found, sending text-only review.")

    # Fallback to text message
    resp = requests.post(
        f"{API}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": caption,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup,
        },
        timeout=120,
    )
    resp.raise_for_status()
    print(f"Sent draft {draft_id} for review via text.")


if __name__ == "__main__":
    draft_id = sys.argv[1]
    with open("output/script.json") as f:
        script_data = json.load(f)
        
    preview_path = os.environ.get("PREVIEW_PATH", "output/preview.mp4")
    send_for_review(
        draft_id,
        preview_path,
        script_data["caption_title"],
        script_data["hashtags"],
    )
