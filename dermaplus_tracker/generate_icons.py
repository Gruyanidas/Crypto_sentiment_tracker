"""
Generate PWA icons for Derma Plus app.
Colors match the brand: teal #2d8fad + lime-green #8dc63f.

To replace with the real logo:
  1. Save your logo PNG as logo_source.png in this folder
  2. Run:  python replace_icon.py
"""

from PIL import Image, ImageDraw, ImageFont
import os, math

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

TEAL  = (45,  143, 173)
GREEN = (141, 198,  63)
BG    = (6,   14,  19)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_icon(size):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad  = int(size * 0.04)
    r    = size // 2

    # dark rounded background
    draw.rounded_rectangle([0, 0, size-1, size-1],
                           radius=int(size * 0.22), fill=BG + (255,))

    # teal-to-green gradient ring
    ring_w = max(3, int(size * 0.055))
    steps  = 360
    for i in range(steps):
        t     = i / steps
        color = lerp_color(TEAL, GREEN, t)
        angle = math.radians(i - 90)
        x0 = r + (r - pad - ring_w) * math.cos(angle)
        y0 = r + (r - pad - ring_w) * math.sin(angle)
        x1 = r + (r - pad)          * math.cos(angle)
        y1 = r + (r - pad)          * math.sin(angle)
        draw.line([(x0, y0), (x1, y1)], fill=color + (255,), width=2)

    # two green leaf / wing shapes (butterfly reference)
    cx, cy = size // 2, int(size * 0.42)
    lw, lh = int(size * 0.18), int(size * 0.24)
    for side in (-1, 1):
        ox   = cx + side * int(size * 0.13)
        oy   = cy - int(size * 0.06)
        bbox = [ox - lw//2, oy - lh//2, ox + lw//2, oy + lh//2]
        draw.ellipse(bbox, fill=GREEN + (190,))

    # "D" in teal, "P" in green
    font_size = int(size * 0.32)
    font = None
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ]:
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except OSError:
            pass
    if font is None:
        font = ImageFont.load_default()

    text = "DP"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        bd = draw.textbbox((0, 0), "D", font=font)
        w_d = bd[2] - bd[0]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)
        w_d, _ = draw.textsize("D", font=font)

    tx = (size - tw) // 2
    ty = int(size * 0.50)
    draw.text((tx,       ty), "D", font=font, fill=TEAL  + (255,))
    draw.text((tx + w_d, ty), "P", font=font, fill=GREEN + (255,))

    # gradient underline
    ul_y  = ty + th + int(size * 0.04)
    ul_w  = int(tw * 0.8)
    ul_x0 = (size - ul_w) // 2
    ul_h  = max(2, int(size * 0.018))
    for px in range(ul_w):
        color = lerp_color(TEAL, GREEN, px / ul_w)
        draw.rectangle([ul_x0 + px, ul_y, ul_x0 + px, ul_y + ul_h],
                       fill=color + (220,))
    return img


for sz in [192, 512]:
    path = os.path.join(STATIC, f"icon-{sz}.png")
    make_icon(sz).save(path)
    print(f"Saved {path}")

print("Done.")
