"""Send a non-blocking status notification after an automated workflow run."""
import os

import requests


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram notification skipped: credentials are not configured.")
        return

    status = os.environ.get("WORKFLOW_STATUS", "unknown").upper()
    publish = os.environ.get("PUBLISH", "false") == "true"
    url = os.environ.get("WORKFLOW_URL", "")
    yt_url = os.environ.get("YOUTUBE_URL", "")
    
    title = "video"
    if publish and os.path.exists("output/approved/script.json"):
        import json
        try:
            with open("output/approved/script.json") as f:
                title = json.load(f).get("caption_title", "video")
        except Exception:
            pass

    if publish and status == "SUCCESS":
        text = f"✅ Posted! \"{title}\" is now live on YouTube.\n🔗 {yt_url}\n\n📊 Check the run: {url}"
    else:
        mode = "YouTube upload" if publish else "draft generation"
        text = f"Daily reels workflow: {status} ({mode})."
        if url:
            text += f"\n{url}"

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram notification failed (non-fatal): {e} — Response: {response.text}")


if __name__ == "__main__":
    main()
