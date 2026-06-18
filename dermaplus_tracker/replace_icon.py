"""
Konvertuje Derma Plus logo u PWA ikone.

Upotreba:
  1. Snimi logo sliku kao  logo.png  u ovaj folder (Dermaplus_termini/)
  2. Pokreni:  python replace_icon.py
"""

from PIL import Image
import os

BASE   = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")
SRC    = os.path.join(BASE, "logo.png")
BG     = (6, 14, 19)       # tamna pozadina (#060e13)
PAD    = 0.14              # 14% padding od ruba

if not os.path.exists(SRC):
    print("GREŠKA: logo.png ne postoji vo овој folder.")
    print(f"  Stavi logo na: {SRC}")
    exit(1)

logo = Image.open(SRC).convert("RGBA")

for size in [192, 512]:
    icon = Image.new("RGBA", (size, size), BG + (255,))

    # izračunaj veličinu loga sa paddingom
    pad_px  = int(size * PAD)
    max_dim = size - 2 * pad_px

    # proporcionalno smanjivanje
    lw, lh = logo.size
    scale  = min(max_dim / lw, max_dim / lh)
    nw, nh = int(lw * scale), int(lh * scale)
    resized = logo.resize((nw, nh), Image.LANCZOS)

    # centriraj na tamnoj pozadini
    x = (size - nw) // 2
    y = (size - nh) // 2
    icon.paste(resized, (x, y), resized)

    out = os.path.join(STATIC, f"icon-{size}.png")
    icon.save(out)
    print(f"Saved {out}")

print("Gotovo! Uradi git add static/icon-*.png && git commit -m 'Update icons with real logo' && git push")
