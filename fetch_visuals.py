"""
Stage 3: Visuals.

Pulls free, no-watermark vertical stock video clips from Pexels matching
the script's visual_keywords. Falls back to Pixabay if you prefer — same
pattern, different endpoint.

Output: output/clips/clip_0.mp4, clip_1.mp4, ...
"""
import json
import os

from dotenv import load_dotenv

load_dotenv()

import requests

PEXELS_API = "https://api.pexels.com/videos/search"


def fetch_clip(keyword: str, out_path: str, min_duration=4) -> bool:
    headers = {"Authorization": os.environ["PEXELS_API_KEY"]}
    params = {"query": keyword, "orientation": "portrait", "per_page": 5}

    resp = requests.get(PEXELS_API, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    results = resp.json().get("videos", [])

    for video in results:
        if video["duration"] < min_duration:
            continue
        # pick the highest-res vertical file available
        files = sorted(
            video["video_files"], key=lambda f: f.get("height", 0), reverse=True
        )
        portrait_files = [f for f in files if f.get("height", 0) > f.get("width", 1)]
        chosen = (portrait_files or files)[0]

        video_data = requests.get(chosen["link"], timeout=60).content
        with open(out_path, "wb") as f:
            f.write(video_data)
        return True

    return False


def main():
    with open("output/script.json") as f:
        script_data = json.load(f)

    keywords = script_data["visual_keywords"]
    os.makedirs("output/clips", exist_ok=True)

    fetched = 0
    for i, kw in enumerate(keywords):
        out_path = f"output/clips/clip_{i}.mp4"
        if fetch_clip(kw, out_path):
            fetched += 1
            print(f"Fetched clip for '{kw}' -> {out_path}")
        else:
            print(f"No result for '{kw}', skipping")

    if fetched == 0:
        raise RuntimeError("No visuals could be fetched — check PEXELS_API_KEY")


if __name__ == "__main__":
    main()
