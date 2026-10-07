"""Dev tool: regenerate assets/app.ico (needs Pillow)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.preview_icons import render  # noqa: E402

def make(size=256):
    S = 4
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, size * S - 1, size * S - 1], radius=int(size * S * 0.22), fill=(59, 76, 202, 255))
    img = img.resize((size, size), Image.LANCZOS)
    glyph = render("hub", int(size * 0.62), color=(255, 255, 255), bg=(59, 76, 202)).convert("RGBA")
    off = (size - glyph.width) // 2
    mask = Image.new("L", glyph.size, 0)
    gd = glyph.convert("RGB")
    # keep only the white glyph pixels over the accent background
    px = gd.load(); m = mask.load()
    for x in range(glyph.width):
        for y in range(glyph.height):
            r, g, b = px[x, y]
            m[x, y] = max(0, min(255, int((r - 59) / (255 - 59) * 255)))
    white = Image.new("RGBA", glyph.size, (255, 255, 255, 255)); white.putalpha(mask)
    img.alpha_composite(white, (off, off))
    return img

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets" / "app.ico"
    make().save(out, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    make().save(out.with_suffix(".png"))
    print("wrote", out)
