"""Check approval status from the webhook payload and download the draft if approved."""
import os
import sys
import subprocess


def download_release_asset(draft_id: str, asset_name: str, out_path: str) -> bool:
    """Uses gh CLI (preinstalled on GitHub Actions runners) to pull a release asset."""
    result = subprocess.run(
        ["gh", "release", "download", draft_id, "--pattern", asset_name, "--output", out_path, "--clobber"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Failed to download {asset_name}: {result.stderr}")
    return result.returncode == 0


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    action = os.environ.get("DISPATCH_ACTION")
    draft_id = os.environ.get("DISPATCH_DRAFT_ID")

    approved = False

    if event_name == "repository_dispatch":
        print(f"Triggered by repository_dispatch. Action: {action}, Draft: {draft_id}")
        if action == "telegram_approved":
            os.makedirs("output/approved", exist_ok=True)
            video_ok = download_release_asset(draft_id, "final.mp4", "output/approved/final.mp4")
            meta_ok = download_release_asset(draft_id, "script.json", "output/approved/script.json")
            if video_ok and meta_ok:
                approved = True
            else:
                print("Failed to download release assets. Cannot proceed with posting.")
        elif action == "telegram_rejected":
            print(f"Draft {draft_id} was rejected. Deleting release...")
            subprocess.run(["gh", "release", "delete", draft_id, "--yes", "--cleanup-tag"], check=False)
            print("Deleted.")
    else:
        print("Not triggered by Telegram webhook.")

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"approved={'true' if approved else 'false'}\n")
        f.write(f"draft_id={draft_id or ''}\n")


if __name__ == "__main__":
    main()
