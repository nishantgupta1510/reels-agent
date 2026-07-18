from PIL import Image, ImageDraw, ImageFont

width, height = 300, 100
image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Draw magnifying glass icon
draw.ellipse((15, 25, 55, 65), outline="white", width=4)
draw.line((48, 58, 70, 80), fill="white", width=5)

# Try loading font, fallback to default
try:
    font = ImageFont.truetype("fonts/NotoSansDevanagari-Bold.ttf", 45)
except Exception:
    font = ImageFont.load_default()

draw.text((85, 22), "Raaz", fill="white", font=font)
image.save("assets/logo.png")
print("Saved assets/logo.png successfully")
