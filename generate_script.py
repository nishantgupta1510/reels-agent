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
import re
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a short-form video scriptwriter for YouTube Shorts \
and Instagram Reels. You write tight, high-retention scripts in Hindi (Devanagari \
script). Start with a surprising or counter-intuitive fact that most people \
don't know. Use conversational Hindi, not textbook Hindi. A scroll-stopping \
hook in the first line, punchy short sentences, a clear payoff, and a soft \
call-to-action at the end. Output ONLY valid JSON, no markdown fences, no \
commentary, matching exactly this schema:

{{
  "topic": string,
  "hook": string,
  "script": string,
  "visual_keywords": [string, string, string, string, string],
  "caption_title": string,
  "hashtags": [string, string, string, string, string] // Mix of Hindi and English
}}

The "script" field is the full voiceover text, written to be read aloud in \
about {seconds} seconds (roughly {words} words). "visual_keywords" are \
cinematic, scene-specific stock-footage search terms (e.g., "maglev train \
japan aerial", "glowing neon city time lapse") that visually match the \
script's mood/content — avoid boring generic terms or anything copyrighted."""


def generate_script(niche: str, seconds: int = 30) -> dict:
    client = OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL") or "https://api.groq.com/openai/v1",
    )
    words = int(seconds * 2.5)  # ~150 wpm spoken pace

    required_keys = {"topic", "hook", "script", "visual_keywords", "caption_title", "hashtags"}
    last_error = None
    temperature = 0.9

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=os.environ.get("LLM_MODEL") or "llama-3.3-70b-versatile",
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
                temperature=temperature,
            )

            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences carefully
            raw = re.sub(r'^```\w*\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            
            data = json.loads(raw)
            
            # Schema validation
            if not required_keys.issubset(data.keys()):
                raise ValueError(f"Missing keys in JSON: {required_keys - data.keys()}")

            data["hashtags"] = [
                h if h.startswith("#") else f"#{h}" for h in data.get("hashtags", [])
            ]
            return data

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            last_error = e
            temperature += 0.1  # slightly increase randomness on retry
            time.sleep(1)

    raise RuntimeError(f"Failed to generate valid script after 3 attempts. Last error: {last_error}")


if __name__ == "__main__":
    niche = os.environ.get("NICHE") or "interesting science facts"
    seconds = int(os.environ.get("VIDEO_LENGTH_SECONDS") or 55)

    result = generate_script(niche, seconds)

    os.makedirs("output", exist_ok=True)
    with open("output/script.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
