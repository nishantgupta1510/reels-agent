"""
Stage 1: Idea + script generation.

Works with ANY OpenAI-compatible API — point LLM_BASE_URL at a free
provider (Groq, Gemini's OpenAI-compat endpoint, etc.) to test at $0.

Output: output/script.json
{
  "topic": "...",
  "hook": "first 3 seconds — the make-or-break line",
  "script": "full voiceover text",
  "visual_keywords": ["keyword1", "keyword2", ...],  # for stock footage search
  "caption_title": "short title for the post",
  "hashtags": ["#...", "#..."]
}
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a short-form video scriptwriter for YouTube Shorts \
and Instagram Reels. You write tight, high-retention scripts: a scroll-stopping \
hook in the first line, punchy short sentences, a clear payoff, and a soft \
call-to-action at the end. Output ONLY valid JSON, no markdown fences, no \
commentary, matching exactly this schema:

{{
  "topic": string,
  "hook": string,
  "script": string,
  "visual_keywords": [string, string, string, string, string],
  "caption_title": string,
  "hashtags": [string, string, string, string, string]
}}

The "script" field is the full voiceover text, written to be read aloud in \
about {seconds} seconds (roughly {words} words). "visual_keywords" are \
generic, stock-footage-searchable terms (e.g. "ocean waves", "city traffic \
night") that visually match the script's mood/content — avoid anything \
copyrighted or brand-specific."""


def generate_script(niche: str, seconds: int = 30) -> dict:
    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    )
    words = int(seconds * 2.5)  # ~150 wpm spoken pace

    resp = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(seconds=seconds, words=words),
            },
            {
                "role": "user",
                "content": f"Niche: {niche}\nGenerate one script for today.",
            },
        ],
        temperature=0.9,
    )

    raw = resp.choices[0].message.content.strip()
    # Strip accidental markdown fences if the model adds them
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    data["hashtags"] = [
        h if h.startswith("#") else f"#{h}" for h in data.get("hashtags", [])
    ]
    return data


if __name__ == "__main__":
    niche = os.environ.get("NICHE", "interesting science facts")
    seconds = int(os.environ.get("VIDEO_LENGTH_SECONDS", 30))

    result = generate_script(niche, seconds)

    os.makedirs("output", exist_ok=True)
    with open("output/script.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
