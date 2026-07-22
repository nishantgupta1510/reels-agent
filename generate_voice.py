"""
Stage 2: Voiceover generation.

Two providers, switched with TTS_PROVIDER in .env:

  TTS_PROVIDER=edge         (default) — edge-tts, free, unofficial MS wrapper
  TTS_PROVIDER=elevenlabs   — ElevenLabs, paid tier for commercial use,
                              noticeably more natural/human-sounding

Both paths produce the same two outputs so nothing downstream (assembly,
captions) needs to know which one ran:
  output/voice.mp3
  output/word_timings.json   -> [{"word", "start_ms", "duration_ms"}, ...]
"""
import asyncio
import base64
import json
import os

import edge_tts
import requests
from dotenv import load_dotenv

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    HAS_TRANSLITERATION = True
except ImportError:
    HAS_TRANSLITERATION = False
    print("Warning: indic-transliteration not installed. Roman captions will use Devanagari fallback.")

load_dotenv()

# Good default voices — browse more with: `edge-tts --list-voices`
EDGE_VOICE = os.environ.get("TTS_VOICE") or "en-US-GuyNeural"


async def synthesize_edge(text: str, out_path: str) -> list:
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    word_timings = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append(
                    {
                        "word": chunk["text"],
                        "start_ms": chunk["offset"] / 10000,  # 100ns -> ms
                        "duration_ms": chunk["duration"] / 10000,
                    }
                )
    return word_timings


def synthesize_elevenlabs(text: str, out_path: str) -> list:
    """
    Uses the /with-timestamps endpoint so we get character-level alignment
    in the same request as the audio — no separate transcription step needed.
    Docs: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps

    Requires ELEVENLABS_API_KEY and ELEVEN_VOICE_ID in .env. To get a
    voice_id: elevenlabs.io -> Voice Library -> filter Accent: Indian ->
    add a voice you like -> copy its Voice ID from "My Voices".
    """
    voice_id = os.environ["ELEVEN_VOICE_ID"]
    api_key = os.environ["ELEVENLABS_API_KEY"]
    model_id = os.environ.get("ELEVEN_MODEL_ID", "eleven_multilingual_v2")

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["audio_base64"]))

    alignment = data["alignment"]
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]

    # Group character-level timing into word-level timing (matches the
    # schema edge-tts produces, so assemble_video.py needs no changes)
    word_timings = []
    current_word, word_start, word_end = "", None, None
    for ch, s, e in zip(chars, starts, ends):
        if ch.strip() == "":
            if current_word:
                word_timings.append(
                    {
                        "word": current_word,
                        "start_ms": word_start * 1000,
                        "duration_ms": (word_end - word_start) * 1000,
                    }
                )
            current_word, word_start, word_end = "", None, None
        else:
            word_start = s if word_start is None else word_start
            current_word += ch
            word_end = e
    if current_word:
        word_timings.append(
            {
                "word": current_word,
                "start_ms": word_start * 1000,
                "duration_ms": (word_end - word_start) * 1000,
            }
        )
    return word_timings


import re

def romanize_timings(word_timings: list) -> list:
    """Transliterate a list of word-timing dicts from Devanagari to natural Roman script."""
    if not HAS_TRANSLITERATION:
        return word_timings
    roman = []
    
    # Custom dictionary for English loanwords and user preferences
    dictionary = {
        'strit': 'street', 'phud': 'food', 'phemas': 'famous', 'batar': 'butter',
        'chikan': 'chicken', 'kanat': 'connaught', 'ples': 'place', 
        'kachaudi': 'kachaudi', 'men': 'me', 'hain': 'hai', 'hon': 'ho',
        'mat': 'maat', 'jaen': 'jayen', 'shaukin': 'shaukeen', 'asali': 'asli',
        'hotal': 'hotal', 'svad': 'svad', 'jarur': 'jarur', 'namaste': 'namaste',
        'sabako': 'sabko', 'jisaka': 'jiska', 'janate': 'jante', 'apane': 'aapne',
        'apako': 'apko', 'itana': 'itna', 'janane': 'janne', 'karana': 'karna',
        'bat': 'baat', 'kanal': 'channel', 'phalau': 'follow'
    }

    for entry in word_timings:
        try:
            # Get raw ITRANS
            raw = transliterate(entry["word"], sanscript.DEVANAGARI, sanscript.ITRANS)
            
            # 1. Remove trailing schwa (lowercase 'a') before lowercasing everything
            if len(raw) > 2 and raw.endswith('a') and raw[-2] not in 'aeiouAEIOU':
                raw = raw[:-1]
                
            # 2. Handle ITRANS Anusvara (M or .N) safely before lowercase
            raw = raw.replace('.N', 'n').replace('M', 'n')
            
            # 3. Remove ITRANS nukta dots (e.g. .D for ड़ -> D) and Dandas (|)
            raw = raw.replace('.', '').replace('|', '')
                
            # 4. Lowercase everything
            cleaned = raw.lower()
            
            # 5. Simplify vowels (aa -> a, ii -> i, uu -> u)
            cleaned = re.sub(r'a+', 'a', cleaned)
            cleaned = re.sub(r'i+', 'i', cleaned)
            cleaned = re.sub(r'u+', 'u', cleaned)
            
            # 6. Apply dictionary overrides (perfect English spellings & schwas)
            if cleaned in dictionary:
                cleaned = dictionary[cleaned]
                
            roman_word = cleaned.strip()
        except Exception:
            roman_word = entry["word"]
        roman.append({**entry, "word": roman_word})
    return roman


def main():
    with open("output/script.json") as f:
        script_data = json.load(f)

    text = script_data["script"]
    os.makedirs("output", exist_ok=True)

    provider = (os.environ.get("TTS_PROVIDER") or "edge").lower()
    if provider == "elevenlabs":
        word_timings = synthesize_elevenlabs(text, "output/voice.mp3")
    else:
        word_timings = asyncio.run(synthesize_edge(text, "output/voice.mp3"))

    with open("output/word_timings.json", "w") as f:
        json.dump(word_timings, f, indent=2)

    # Also produce romanized timings for on-screen captions
    roman_timings = romanize_timings(word_timings)
    with open("output/roman_word_timings.json", "w") as f:
        json.dump(roman_timings, f, indent=2)

    print(f"Voice saved to output/voice.mp3 via '{provider}' ({len(word_timings)} words timed)")


if __name__ == "__main__":
    main()
