"""
Stage 6: Approval check (runs every ~10 min via its own cron workflow).

Polls Telegram for button presses since the last check. On Approve, downloads
the corresponding draft from its GitHub Release and posts it to YouTube +
Instagram. On Reject, just cleans it up. Prints a shell-friendly summary
that the workflow YAML uses to decide whether to run the posting step.
"""
import json
import os
import subprocess

import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET_FILE = "output/telegram_offset.txt"


def get_offset() -> int:
    if os.path.exists(OFFSET_FILE):
        return int(open(OFFSET_FILE).read().strip() or 0)
    return 0


def save_offset(offset: int):
    os.makedirs("output", exist_ok=True)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def answer_callback(callback_id: str, text: str):
    requests.post(
        f"{API}/answerCallbackQuery",
        json={"callback_query_id": callback_id, "text": text},
        timeout=20,
    )


def download_release_asset(draft_id: str, asset_name: str, out_path: str) -> bool:
    """Uses gh CLI (preinstalled on GitHub Actions runners) to pull a release asset."""
    result = subprocess.run(
        ["gh", "release", "download", draft_id, "--pattern", asset_name, "--output", out_path, "--clobber"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def delete_release(draft_id: str):
    subprocess.run(["gh", "release", "delete", draft_id, "--yes", "--cleanup-tag"], capture_output=True)


def main():
    offset = get_offset()
    resp = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 5}, timeout=30)
    resp.raise_for_status()
    updates = resp.json().get("result", [])

    actions_taken = []

    for update in updates:
        offset = max(offset, update["update_id"] + 1)
        cq = update.get("callback_query")
        if not cq:
            continue

        action, draft_id = cq["data"].split(":", 1)

        if action == "approve":
            os.makedirs("output/approved", exist_ok=True)
            video_ok = download_release_asset(draft_id, "final.mp4", "output/approved/final.mp4")
            meta_ok = download_release_asset(draft_id, "script.json", "output/approved/script.json")
            if video_ok and meta_ok:
                actions_taken.append(draft_id)
                answer_callback(cq["id"], "Approved — posting now!")
            else:
                answer_callback(cq["id"], "Couldn't find that draft (maybe already handled).")
        elif action == "reject":
            delete_release(draft_id)
            answer_callback(cq["id"], "Rejected — discarded.")

    save_offset(offset)

    # Signal to the workflow YAML whether a post should happen
    with open("output/approved_draft_id.txt", "w") as f:
        f.write(actions_taken[0] if actions_taken else "")

    print(f"Processed {len(updates)} updates. Approved drafts: {actions_taken}")


if __name__ == "__main__":
    main()
