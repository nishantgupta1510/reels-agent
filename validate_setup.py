"""
Run this after updating .env with your rotated credentials.
Checks each one with a lightweight call that doesn't spend meaningful
quota or post/send anything real. Prints a clear PASS/FAIL per item,
including the actual API error body on failure (not just the status code).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

results = []


def check(name, fn):
    try:
        detail = fn()
        results.append((name, True, detail))
    except Exception as e:
        results.append((name, False, str(e)))


def raise_with_body(resp):
    """Surface the actual API error message, not just the HTTP status."""
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")


def check_elevenlabs():
    key = os.environ["ELEVENLABS_API_KEY"]
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": key},
        timeout=20,
    )
    raise_with_body(resp)
    return f"authenticated as account tier: {resp.json().get('subscription', {}).get('tier', 'unknown')}"


def check_pexels():
    key = os.environ["PEXELS_API_KEY"]
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": key},
        params={"query": "test", "per_page": 1},
        timeout=20,
    )
    raise_with_body(resp)
    return "key valid, search returned results"


def check_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
    raise_with_body(resp)
    bot_name = resp.json()["result"]["username"]
    return f"bot token valid, bot is @{bot_name}"


def check_instagram():
    ig_id = os.environ["IG_BUSINESS_ACCOUNT_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    resp = requests.get(
        f"https://graph.facebook.com/v25.0/{ig_id}",
        params={"fields": "username", "access_token": token},
        timeout=20,
    )
    raise_with_body(resp)
    return f"token + account ID valid, linked to @{resp.json().get('username')}"


def check_youtube():
    # Only confirms OAuth completed and a token was cached — deliberately
    # does NOT call channels.list(), which needs broader scope than the
    # youtube.upload scope this pipeline actually requests and needs.
    from post_social import get_youtube_client, TOKEN_PATH

    get_youtube_client()
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError("token file was not created")
    return "OAuth completed, upload-scope token cached"


print("Validating credentials...\n")
check("ElevenLabs", check_elevenlabs)
check("Pexels", check_pexels)
check("Telegram", check_telegram)
check("Instagram", check_instagram)
check("YouTube", check_youtube)

print()
for name, ok, detail in results:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")

failed = [r for r in results if not r[1]]
if failed:
    print(f"\n{len(failed)} check(s) failed — see details above.")
else:
    print("\nAll 5 credentials validated successfully.")
