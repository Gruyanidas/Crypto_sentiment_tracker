"""
Generate PWA icons for Derma Plus.

Produces:
  dermaplus_tracker/static/icon-192.png
  dermaplus_tracker/static/icon-512.png

Background : #1e1416  (dark rose-black)
Text       : "DP" in Cormorant Garamond / serif, colour #e8d2d4
Ring       : #944854  (rose / primary)
Underline  : small decorative line below text
"""

import os
import math

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit(
        "Pillow is required. Install it with:  pip install Pillow"
    )

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(SCRIPT_DIR, "static")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BG_COLOR    = "#1e1416"
TEXT_COLOR  = "#e8d2d4"
RING_COLOR  = "#944854"
TEXT        = "DP"

# Font search order (first match wins; falls back to default)
FONT_NAMES  = [
    "CormorantGaramond-Bold.ttf",
    "CormorantGaramond-Regular.ttf",
    "Georgia Bold.ttf",
    "Georgia.ttf",
    "DejaVuSerif-Bold.ttf",
    "DejaVuSerif.ttf",
    "LiberationSerif-Bold.ttf",
    "LiberationSerif-Regular.ttf",
]
FONT_DIRS   = [
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    "C:\\Windows\\Fonts",
]


def find_font():
    for font_dir in FONT_DIRS:
        if not os.path.isdir(font_dir):
            continue
        for root, _dirs, files in os.walk(font_dir):
            for name in FONT_NAMES:
                if name.lower() in (f.lower() for f in files):
                    for f in files:
                        if f.lower() == name.lower():
                            return os.path.join(root, f)
    return None


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_icon(size: int) -> Image.Image:
    scale = 4                        # super-sample for anti-aliasing
    S     = size * scale

    img  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_rgb   = hex_to_rgb(BG_COLOR)
    ring_rgb = hex_to_rgb(RING_COLOR)
    text_rgb = hex_to_rgb(TEXT_COLOR)

    # --- Rounded rectangle background ---
    corner_r = S // 5
    draw.rounded_rectangle([0, 0, S - 1, S - 1], radius=corner_r, fill=bg_rgb + (255,))

    # --- Decorative ring (arc / circle outline) ---
    ring_w    = max(2, S // 36)
    ring_pad  = S // 10
    draw.ellipse(
        [ring_pad, ring_pad, S - ring_pad, S - ring_pad],
        outline=ring_rgb + (200,),
        width=ring_w,
    )

    # --- Text ---
    font_size = S // 3
    font_path = find_font()
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox   = draw.textbbox((0, 0), TEXT, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx     = (S - tw) // 2 - bbox[0]
    ty     = (S - th) // 2 - bbox[1] - S // 20   # shift up slightly

    draw.text((tx, ty), TEXT, fill=text_rgb + (255,), font=font)

    # --- Decorative underline ---
    ul_w    = int(tw * 0.55)
    ul_x    = (S - ul_w) // 2
    ul_y    = ty + th + S // 18
    ul_h    = max(2, S // 60)
    draw.rounded_rectangle(
        [ul_x, ul_y, ul_x + ul_w, ul_y + ul_h],
        radius=ul_h // 2,
        fill=ring_rgb + (200,),
    )

    # --- Downsample ---
    img = img.resize((size, size), Image.LANCZOS)
    return img


for size in (192, 512):
    icon = draw_icon(size)
    path = os.path.join(OUTPUT_DIR, f"icon-{size}.png")
    icon.save(path)
    print(f"  Saved {path}")

print("Done.")
