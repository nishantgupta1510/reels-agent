import os
import requests
from fastapi import FastAPI, Request, BackgroundTasks

app = FastAPI()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPO")  # e.g., "nishantgupta1510/reels-agent"

@app.post("/telegram")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    cq = data.get("callback_query")
    if not cq:
        return {"status": "ok"}
        
    try:
        action, draft_id = cq["data"].split(":", 1)
    except ValueError:
        return {"status": "ok"}
        
    chat_id = str(cq.get("message", {}).get("chat", {}).get("id", ""))
    message_text = cq.get("message", {}).get("text", "")
    
    # Extract title from message text if available (assumes format 🎬 *Title*\n...)
    title = "your video"
    if "🎬 " in message_text:
        title = message_text.split("🎬 ")[1].split("\n")[0].strip("* ")
        
    # We define a background task to handle the slow API calls (GitHub + Telegram message)
    def process_approval(title, action, draft_id, chat_id):
        event_type = "telegram_approved" if action == "approve" else "telegram_rejected"
        gh_response = requests.post(
            f"https://api.github.com/repos/{REPO}/dispatches",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {GH_TOKEN}"
            },
            json={
                "event_type": event_type,
                "client_payload": {
                    "draft_id": draft_id
                }
            },
            timeout=10
        )
        gh_ok = gh_response.status_code in (200, 204)
        
        if action == "approve" and gh_ok:
            notify_msg = (
                f"⏳ Got it! \"{title}\" is being uploaded to YouTube now.\n"
                f"You'll get a confirmation once it's live."
            )
        elif action == "reject":
            notify_msg = f"🗑️ Draft \"{title}\" discarded."
        else:
            notify_msg = f"⚠️ Failed to trigger GitHub Action: {gh_response.status_code} {gh_response.text}"
            
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": notify_msg
            },
            timeout=10
        )

    # 1. Dispatch the slow work to the background immediately
    background_tasks.add_task(process_approval, title, action, draft_id, chat_id)
    
    # 2. Answer the callback query instantly to stop the loading spinner (this shows the toast)
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        json={
            "callback_query_id": cq["id"],
            "text": "Approved! Uploading now..." if action == "approve" else "Rejected. Draft deleted."
        },
        timeout=5
    )
    
    return {"status": "ok"}

@app.get("/")
def health_check():
    return {"status": "healthy"}
