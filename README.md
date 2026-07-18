# Reels Agent — Automated Faceless Shorts/Reels Pipeline

Automated draft creation: idea → script → voiceover → visuals → assembled
video → Telegram review. A YouTube Short is posted only after you tap
**Approve** in Telegram. Instagram is intentionally disabled for now.

## How it works

Two GitHub Actions cron jobs:

1. **`generate.yml`** runs once each day at 09:17 UTC / 14:47 IST and sends a
   finished draft with Approve and Reject buttons to Telegram.
2. **`check_approvals.yml`** checks Telegram roughly every ten minutes. An
   approved draft is uploaded to YouTube; a rejected draft is deleted.

No server to keep running. GitHub temporarily stores each draft in a private
draft Release until you approve or reject it. The YouTube upload is `unlisted`
by default.

## Setup order (test each stage for $0 before wiring together)

### 1. LLM for script generation — $0 to test
Get a free API key from **Groq** (console.groq.com — free tier, fast Llama
models) or **Google AI Studio** (free Gemini tier). Put it in `.env` as
`LLM_API_KEY` and `LLM_BASE_URL` (see `.env.example`).
Test: `python generate_script.py` — should print a JSON script to console.

### 2. Voiceover — $0, no signup needed
`edge-tts` is free and open-source, no API key required.
Test: `python generate_voice.py` — should output `output/voice.mp3` +
`output/word_timings.json`.

### 3. Visuals — $0 to test
Free API key from **pexels.com/api** (instant, no credit card).
Put it in `.env` as `PEXELS_API_KEY`.
Test: `python fetch_visuals.py` — downloads a few stock clips to `output/clips/`.

### 4. Video assembly — $0, local compute
Test: `python assemble_video.py` — should produce `output/final.mp4`.
Watch it. This is the step to tune (font size, pacing, clip length) before
you automate anything.

### 5. Telegram approval — $0
- Message **@BotFather** on Telegram → `/newbot` → get a bot token (free, instant)
- Message your new bot once (so it can message you back) → get your chat ID
  by visiting `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Put both in `.env`
Test: `python telegram_review.py test-draft` — it should send the assembled
video with Approve and Reject buttons to your phone.

### 6. YouTube posting — $0 to test
- Google Cloud Console → new project → enable **YouTube Data API v3** →
  create OAuth credentials (Desktop app type) → download `client_secret.json`
- First run opens a browser once to authorize your channel; token is cached
  after that
Test: post to a **private/unlisted** video first — free, within the default
10,000-unit daily quota (~6 uploads/day worth).

### 7. Instagram posting — deferred
- Convert your Instagram account to a **Business** or **Creator** account
  (free, in-app)
- Link it to a Facebook Page (free)
- Create a Meta developer app at developers.facebook.com (free) → get a
  long-lived access token for your own account (no app review needed for
  posting to *your own* account)
Instagram is disabled in the current workflows. You can leave the account
private; nothing in this project will attempt to post to it. We will configure
it separately after the YouTube approval flow is working.

### 8. Wire it together
Once every script above works standalone, push to GitHub, add all the
needed values as **GitHub Secrets** (Settings → Secrets → Actions), and
enable both files in `.github/workflows/`. Required secrets are
`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `NICHE`, `PEXELS_API_KEY`,
`YOUTUBE_TOKEN_JSON`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`.
Instagram secrets are not required for the YouTube-only workflow.

Set the repository variable `YOUTUBE_PRIVACY_STATUS` to `unlisted` for your
first live test. Change it to `public` only after verifying the YouTube post.

GitHub can disable scheduled workflows after 60 days with no repository
activity. Keep an eye on the Telegram status message, and re-enable the
workflow from the Actions tab if it is ever disabled.

## Where "small investment" actually helps later

Everything above is $0 to build and test. The only places worth spending
once the channel has traction:
- A paid LLM tier if you outgrow free daily limits (~$1–5/mo)
- A paid TTS voice (ElevenLabs) if you want a specific branded voice
- Stock footage subscription (Storyblocks etc.) if Pexels/Pixabay feel
  repetitive across videos
- AI-generated (not stock) visuals, once you want a distinct look

None of these are required to launch and test the full pipeline.
