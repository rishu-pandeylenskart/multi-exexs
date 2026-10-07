"""Dev tool: render every icon to a PNG with Pillow (no Tk needed)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hub.icons import ICONS, icon_primitives

def render(name, size=96, color=(59, 76, 202), bg=(255, 255, 255)):
    S = 4
    img = Image.new("RGB", (size * S, size * S), bg)
    d = ImageDraw.Draw(img); k = size * S / 24; w = max(2, int(1.9 * k))
    for p in icon_primitives(name):
        t = p[0]
        if t in ("l", "c"):
            pts = [(p[1][i] * k, p[1][i + 1] * k) for i in range(0, len(p[1]), 2)]
            if t == "c": pts.append(pts[0])
            d.line(pts, fill=color, width=w, joint="curve")
            for q in (pts[0], pts[-1]): d.ellipse([q[0]-w/2, q[1]-w/2, q[0]+w/2, q[1]+w/2], fill=color)
        elif t == "pf":
            d.polygon([(p[1][i] * k, p[1][i + 1] * k) for i in range(0, len(p[1]), 2)], fill=color)
        else:
            cx, cy, r = p[1] * k, p[2] * k, p[3] * k
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=None if t == "of" else color, fill=color if t == "of" else None, width=w)
    return img.resize((size, size), Image.LANCZOS)

if __name__ == "__main__":
    names = list(ICONS); cols = 8; size = 96
    sheet = Image.new("RGB", (cols * (size + 20), ((len(names) + cols - 1) // cols) * (size + 34)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        x, y = (i % cols) * (size + 20) + 10, (i // cols) * (size + 34) + 6
        sheet.paste(render(n, size), (x, y)); d.text((x, y + size + 4), n, fill=(90, 90, 90))
    sheet.save(sys.argv[1] if len(sys.argv) > 1 else "icons_preview.png")
