"""Extracts a frame and generates a thumbnail with a gradient overlay and text."""
import json
import os
from moviepy.editor import VideoFileClip
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

def generate_thumbnail():
    # 1. Extract frame using MoviePy
    video = VideoFileClip("output/final.mp4")
    # Take a frame at t=2.0s (or middle of video if too short)
    t = min(2.0, video.duration / 2)
    frame = video.get_frame(t)
    
    # 2. Convert to PIL Image
    img = Image.fromarray(frame)
    
    # Resize to YouTube recommended 1280x720, cropping to fit (16:9)
    # The video is 1080x1920 (9:16). We need to crop the center.
    target_width, target_height = 1280, 720
    # Crop middle horizontal slice
    left = 0
    right = 1080
    top = (1920 - int(1080 * target_height / target_width)) // 2
    bottom = top + int(1080 * target_height / target_width)
    img = img.crop((left, top, right, bottom))
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Make the background slightly darker/more saturated for the text to pop
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.2)
    
    # 3. Add dark gradient overlay at bottom
    gradient = Image.new('RGBA', (target_width, target_height), color=0)
    draw = ImageDraw.Draw(gradient)
    for y in range(target_height):
        # Start dark gradient at 40% height down to bottom
        if y > target_height * 0.4:
            alpha = int(255 * ((y - target_height * 0.4) / (target_height * 0.6)))
            draw.line([(0, y), (target_width, y)], fill=(0, 0, 0, min(alpha, 200)))
    img = Image.alpha_composite(img.convert('RGBA'), gradient)
    
    # 4. Add bold text
    with open("output/script.json") as f:
        meta = json.load(f)
    title_text = meta.get("caption_title", "MUST WATCH!").strip()
    
    draw = ImageDraw.Draw(img)
    
    # Try to use the same font as the video
    font_path = "fonts/bold.ttf"
    if not os.path.exists(font_path):
        import glob
        fonts = glob.glob("fonts/*.ttf")
        font_path = fonts[0] if fonts else None
        
    try:
        font = ImageFont.truetype(font_path, 85)
    except:
        font = ImageFont.load_default()
        
    # Draw text with stroke
    # Basic text wrap (simple for titles)
    text_w = font.getbbox(title_text)[2]
    text_h = font.getbbox(title_text)[3]
    x = (target_width - text_w) // 2
    y = target_height - text_h - 60
    
    # Stroke
    stroke_color = "black"
    stroke_width = 4
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), title_text, font=font, fill=stroke_color)
                
    # Fill
    draw.text((x, y), title_text, font=font, fill="yellow")
    
    # Save
    os.makedirs("output", exist_ok=True)
    img.convert('RGB').save("output/thumbnail.jpg", quality=90)
    print("Thumbnail generated at output/thumbnail.jpg")

if __name__ == "__main__":
    generate_thumbnail()
