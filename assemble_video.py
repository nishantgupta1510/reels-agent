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
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
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

    transition_times = []
    current_time = 0.0
    for seg in segments:
        if current_time > 0:
            transition_times.append(current_time)
        current_time += seg.duration

    bg = concatenate_videoclips(segments, method="compose")
    if bg.duration < duration:
        repeats = math.ceil(duration / bg.duration)
        bg = concatenate_videoclips([bg] * repeats, method="compose").subclip(0, duration)
        
        # Add repeated transitions
        extra_transitions = []
        for i in range(1, repeats):
            offset = current_time * i
            extra_transitions.extend([t + offset for t in transition_times])
            extra_transitions.append(offset)
        transition_times.extend(extra_transitions)
        
    return bg.subclip(0, duration), [t for t in transition_times if t < duration]



FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansDevanagari-Bold.ttf")


def build_captions(word_timings: list, total_duration: float, speed_factor: float = 1.15):
    """Group words into ~3-word chunks for punchy, readable captions."""
    chunks = []
    chunk_size = 3
    for i in range(0, len(word_timings), chunk_size):
        group = word_timings[i : i + chunk_size]
        text = " ".join(w["word"] for w in group)
        start = (group[0]["start_ms"] / 1000) / speed_factor
        end = ((group[-1]["start_ms"] + group[-1]["duration_ms"]) / 1000) / speed_factor
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
    SPEED_FACTOR = 1.15
    audio = AudioFileClip("output/voice.mp3").fx(vfx.speedx, SPEED_FACTOR)
    duration = audio.duration

    with open("output/word_timings.json") as f:
        word_timings = json.load(f)

    background, transition_times = build_background(duration)
    background = background.set_audio(audio)
    captions = build_captions(word_timings, duration, speed_factor=SPEED_FACTOR)

    final = CompositeVideoClip([background, *captions], size=(TARGET_W, TARGET_H))
    final = final.set_duration(duration)

    os.makedirs("output", exist_ok=True)
    audio_layers = [final.audio]
    
    # Mix Whoosh SFX at transitions
    whoosh_path = "assets/music/whoosh.wav"
    if os.path.exists(whoosh_path):
        for t in transition_times:
            whoosh = AudioFileClip(whoosh_path).set_start(t).volumex(0.4)
            audio_layers.append(whoosh)

    # Mix Background Music if available
    import glob
    music_files = glob.glob("assets/music/*.wav")
    music_files = [f for f in music_files if "whoosh" not in f]
    if music_files:
        import random
        track = AudioFileClip(random.choice(music_files)).subclip(0, final.duration)
        track = track.volumex(0.30)  # 30% volume
        audio_layers.append(track)
        
    if len(audio_layers) > 1:
        mixed = CompositeAudioClip(audio_layers)
        final = final.set_audio(mixed)

    # Add Raaz Brand Watermark
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        logo_clip = (
            ImageClip(logo_path)
            .set_duration(final.duration)
            .resize(width=180)
            .set_opacity(0.8)
            .set_position((40, TARGET_H - 140))
        )
        final = CompositeVideoClip([final, logo_clip])

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
