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
    mode = "YouTube upload" if publish else "draft generation"
    url = os.environ.get("WORKFLOW_URL", "")
    text = f"Daily reels workflow: {status} ({mode})."
    if url:
        text += f"\n{url}"

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    response.raise_for_status()


if __name__ == "__main__":
    main()
