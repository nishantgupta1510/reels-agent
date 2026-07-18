"""
Stage 4: Assembly.

Combines the fetched clips into a 9:16 video matching the voiceover length,
overlays word-by-word captions (using the free timings from edge-tts), and
exports the final MP4. Pure ffmpeg/MoviePy — no paid service.

Output: output/final.mp4
"""
import glob
import json
import math
import os

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

TARGET_W, TARGET_H = 1080, 1920  # 9:16


def crop_to_vertical(clip):
    """Center-crop any clip to 9:16 without distortion."""
    target_ratio = TARGET_W / TARGET_H
    clip_ratio = clip.w / clip.h
    if clip_ratio > target_ratio:
        new_w = int(clip.h * target_ratio)
        x1 = (clip.w - new_w) // 2
        clip = clip.crop(x1=x1, x2=x1 + new_w)
    else:
        new_h = int(clip.w / target_ratio)
        y1 = (clip.h - new_h) // 2
        clip = clip.crop(y1=y1, y2=y1 + new_h)
    return clip.resize((TARGET_W, TARGET_H))


def build_background(duration: float):
    clip_paths = sorted(glob.glob("output/clips/clip_*.mp4"))
    if not clip_paths:
        raise RuntimeError("No clips found in output/clips — run fetch_visuals.py first")

    segments = []
    remaining = duration
    per_clip = duration / len(clip_paths)

    for path in clip_paths:
        if remaining <= 0:
            break
        raw = VideoFileClip(path)
        if raw.duration <= 0:
            raw.close()
            continue
        seg_len = min(per_clip, raw.duration, remaining)
        seg = crop_to_vertical(raw.subclip(0, seg_len))
        segments.append(seg)
        remaining -= seg_len

    if not segments:
        raise RuntimeError("All downloaded clips were empty or unreadable")

    bg = concatenate_videoclips(segments, method="compose")
    if bg.duration < duration:
        # A search can return only one short clip. Repeat the assembled
        # background enough times to cover the complete voiceover.
        repeats = math.ceil(duration / bg.duration)
        bg = concatenate_videoclips([bg] * repeats, method="compose").subclip(0, duration)
    return bg.subclip(0, duration)



FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansDevanagari-Bold.ttf")


def build_captions(word_timings: list, total_duration: float):
    """Group words into ~3-word chunks for punchy, readable captions."""
    chunks = []
    chunk_size = 3
    for i in range(0, len(word_timings), chunk_size):
        group = word_timings[i : i + chunk_size]
        text = " ".join(w["word"] for w in group)
        start = group[0]["start_ms"] / 1000
        end = (group[-1]["start_ms"] + group[-1]["duration_ms"]) / 1000
        chunks.append((text, start, min(end, total_duration)))

    caption_clips = []
    for text, start, end in chunks:
        if end <= start:
            continue
        txt = TextClip(
            text,
            fontsize=90,
            color="white",
            font=FONT_PATH,
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(TARGET_W - 100, None),
        )
        txt = (
            txt.on_color(
                size=(txt.w + 60, txt.h + 40),
                color=(0, 0, 0),
                pos=("center", "center"),
                col_opacity=0.7,
            )
            .set_position(("center", TARGET_H * 0.7))
            .set_start(start)
            .set_end(end)
        )
        caption_clips.append(txt)
    return caption_clips


def main():
    audio = AudioFileClip("output/voice.mp3")
    duration = audio.duration

    with open("output/word_timings.json") as f:
        word_timings = json.load(f)

    background = build_background(duration).set_audio(audio)
    captions = build_captions(word_timings, duration)

    final = CompositeVideoClip([background, *captions], size=(TARGET_W, TARGET_H))
    final = final.set_duration(duration)

    os.makedirs("output", exist_ok=True)
    # Mix Background Music if available
    import glob
    music_files = glob.glob("assets/music/*.wav")
    if music_files:
        import random
        track = AudioFileClip(random.choice(music_files)).subclip(0, final.duration)
        track = track.volumex(0.12)  # 12% volume
        mixed = CompositeAudioClip([final.audio, track])
        final = final.set_audio(mixed)

    # Add Raaz Brand Watermark
    logo_txt = (
        TextClip("Raaz", fontsize=40, color="white", font=FONT_PATH, stroke_color="black", stroke_width=2)
        .set_position((40, TARGET_H - 120))
        .set_opacity(0.6)
        .set_duration(final.duration)
    )
    final = CompositeVideoClip([final, logo_txt])

    final.write_videofile(
        "output/final.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )


if __name__ == "__main__":
    main()
