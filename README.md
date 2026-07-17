# Reels Agent — Automated Faceless Shorts/Reels Pipeline

Fully automated: idea → script → voiceover → visuals → assembled video →
**you approve on Telegram** → auto-posted to YouTube Shorts + Instagram Reels.

## How it works

Two GitHub Actions cron jobs, both free:

1. **`generate.yml`** (runs once/day) → builds a draft video, sends it to your
   Telegram with Approve/Reject buttons, saves the pending draft's metadata
   as a workflow artifact.
2. **`check_approvals.yml`** (runs every 10 min) → checks Telegram for your
   button press. If approved, uploads to YouTube + Instagram. If rejected,
   discards it.

No server to keep running. No paid hosting. Everything happens inside
GitHub's free compute minutes.

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

### 5. Telegram review gate — $0
- Message **@BotFather** on Telegram → `/newbot` → get a bot token (free, instant)
- Message your new bot once (so it can message you back) → get your chat ID
  by visiting `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Put both in `.env`
Test: `python telegram_review.py` — should send the assembled video to your
phone with Approve/Reject buttons.

### 6. YouTube posting — $0 to test
- Google Cloud Console → new project → enable **YouTube Data API v3** →
  create OAuth credentials (Desktop app type) → download `client_secret.json`
- First run opens a browser once to authorize your channel; token is cached
  after that
Test: post to a **private/unlisted** video first — free, within the default
10,000-unit daily quota (~6 uploads/day worth).

### 7. Instagram posting — $0 to test, needs a one-time setup
- Convert your Instagram account to a **Business** or **Creator** account
  (free, in-app)
- Link it to a Facebook Page (free)
- Create a Meta developer app at developers.facebook.com (free) → get a
  long-lived access token for your own account (no app review needed for
  posting to *your own* account)
Test: post one Reel manually via the API to confirm the token works before
automating.

### 8. Wire it together
Once every script above works standalone, push to GitHub, add all the
`.env` values as **GitHub Secrets** (Settings → Secrets → Actions), and
enable the two workflow files in `.github/workflows/`.

## Where "small investment" actually helps later

Everything above is $0 to build and test. The only places worth spending
once the channel has traction:
- A paid LLM tier if you outgrow free daily limits (~$1–5/mo)
- A paid TTS voice (ElevenLabs) if you want a specific branded voice
- Stock footage subscription (Storyblocks etc.) if Pexels/Pixabay feel
  repetitive across videos
- AI-generated (not stock) visuals, once you want a distinct look

None of these are required to launch and test the full pipeline.
