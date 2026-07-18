from PIL import Image, ImageDraw, ImageFont
import os

width, height = 300, 100
image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Draw a stylized magnifying glass
draw.ellipse((20, 20, 60, 60), outline="white", width=4)
draw.line((55, 55, 80, 80), fill="white", width=6)

# Load font and draw text
try:
    font = ImageFont.truetype("fonts/NotoSansDevanagari-Bold.ttf", 50)
except Exception:
    font = ImageFont.load_default()

draw.text((100, 20), "Raaz", fill="white", font=font)
image.save("assets/logo.png")
