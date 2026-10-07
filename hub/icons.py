"""Vector icons defined as simple primitives on a 24x24 grid.

Drawn with plain canvas lines/ovals so no image files or icon fonts are needed
(works on every Windows version and inside a PyInstaller one-file build).
Primitive kinds:  ("l", pts)  polyline   ("c", pts)  closed polyline
                  ("pf", pts) filled polygon   ("o", cx, cy, r)  circle outline
                  ("of", cx, cy, r) filled circle
"""
from __future__ import annotations

import math


def _arc(cx, cy, r, a0, a1, n=16):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts += [round(cx + r * math.cos(a), 2), round(cy + r * math.sin(a), 2)]
    return pts


def _ellipse(cx, cy, rx, ry, n=24):
    pts = []
    for i in range(n):
        a = math.radians(360 * i / n)
        pts += [round(cx + rx * math.cos(a), 2), round(cy + ry * math.sin(a), 2)]
    return pts


def _star():
    pts = []
    for i in range(10):
        r = 10 if i % 2 == 0 else 4.4
        a = math.radians(-90 + i * 36)
        pts += [round(12 + r * math.cos(a), 2), round(12.8 + r * math.sin(a), 2)]
    return pts


ICONS: dict[str, list[tuple]] = {
    "home": [("l", [3, 11, 12, 3, 21, 11]), ("l", [5, 9.5, 5, 21, 19, 21, 19, 9.5]), ("l", [10, 21, 10, 14, 14, 14, 14, 21])],
    "grid": [("c", [4, 4, 10, 4, 10, 10, 4, 10]), ("c", [14, 4, 20, 4, 20, 10, 14, 10]),
             ("c", [4, 14, 10, 14, 10, 20, 4, 20]), ("c", [14, 14, 20, 14, 20, 20, 14, 20])],
    "star": [("c", _star())],
    "star_filled": [("pf", _star()), ("c", _star())],
    "clock": [("o", 12, 12, 9), ("l", [12, 7, 12, 12, 15.5, 14])],
    "sliders": [("l", [4, 7, 6.5, 7]), ("l", [11.5, 7, 20, 7]), ("o", 9, 7, 2.5),
                ("l", [4, 12, 12.5, 12]), ("l", [17.5, 12, 20, 12]), ("o", 15, 12, 2.5),
                ("l", [4, 17, 5.5, 17]), ("l", [10.5, 17, 20, 17]), ("o", 8, 17, 2.5)],
    "info": [("o", 12, 12, 9), ("l", [12, 11, 12, 16.5]), ("of", 12, 7.8, 1)],
    "search": [("o", 10.5, 10.5, 6.5), ("l", [15.3, 15.3, 20, 20])],
    "refresh": [("l", _arc(12, 12, 8, 40, 330)), ("l", [20, 3.5, 20, 8.5, 15, 8.5])],
    "chevron_left": [("l", [15, 6, 9, 12, 15, 18])],
    "chevron_right": [("l", [9, 6, 15, 12, 9, 18])],
    "folder": [("c", [3, 6.5, 9, 6.5, 11, 9, 21, 9, 21, 19, 3, 19])],
    "arrow_right": [("l", [5, 12, 19, 12]), ("l", [13, 6, 19, 12, 13, 18])],
    "check": [("l", [5, 12.5, 10, 17.5, 19, 7])],
    "alert": [("c", [12, 3.5, 22, 20, 2, 20]), ("l", [12, 10, 12, 14]), ("of", 12, 17, 0.9)],
    "close": [("l", [6, 6, 18, 18]), ("l", [18, 6, 6, 18])],
    "dots": [("of", 12, 5, 1.5), ("of", 12, 12, 1.5), ("of", 12, 19, 1.5)],
    "app": [("c", [3, 5, 21, 5, 21, 19, 3, 19]), ("l", [3, 9, 21, 9])],
    "table": [("c", [4, 5, 20, 5, 20, 19, 4, 19]), ("l", [4, 10, 20, 10]), ("l", [12, 10, 12, 19])],
    "truck": [("c", [2, 6, 14, 6, 14, 17, 2, 17]), ("l", [14, 10, 18, 10, 21.5, 13.5, 21.5, 17, 14, 17]),
              ("o", 7, 18, 2.2), ("o", 17.5, 18, 2.2)],
    "bolt": [("c", [13, 2, 4, 14, 11, 14, 10, 22, 20, 9, 13, 9])],
    "package": [("c", [12, 2.5, 20.5, 7, 20.5, 17, 12, 21.5, 3.5, 17, 3.5, 7]),
                ("l", [3.5, 7, 12, 11.5, 20.5, 7]), ("l", [12, 11.5, 12, 21.5])],
    "plane": [("c", [21, 3, 3, 10.5, 10, 13, 13, 20]), ("l", [21, 3, 10, 13])],
    "globe": [("o", 12, 12, 9), ("l", [3, 12, 21, 12]), ("c", _ellipse(12, 12, 4.2, 9))],
    "hub": [("l", [12, 12, 5, 5]), ("l", [12, 12, 19, 5]), ("l", [12, 12, 5, 19]), ("l", [12, 12, 19, 19]),
            ("of", 12, 12, 2.6), ("of", 5, 5, 2), ("of", 19, 5, 2), ("of", 5, 19, 2), ("of", 19, 19, 2)],
}


def icon_primitives(name: str) -> list[tuple]:
    return ICONS.get(name) or ICONS["app"]


def draw_icon(canvas, name: str, x: float, y: float, size: float, color: str, tags=(), width: float | None = None):
    """Draw icon ``name`` with its top-left corner at (x, y), ``size`` px square."""
    k = size / 24.0
    w = width if width is not None else max(1.5, size / 12.5)

    def tf(pts):
        return [(v * k + (x if i % 2 == 0 else y)) for i, v in enumerate(pts)]

    for prim in icon_primitives(name):
        kind = prim[0]
        if kind in ("l", "c"):
            pts = tf(prim[1])
            if kind == "c":
                pts = pts + pts[:2]
            canvas.create_line(*pts, fill=color, width=w, capstyle="round", joinstyle="round", tags=tags)
        elif kind == "pf":
            canvas.create_polygon(*tf(prim[1]), fill=color, outline=color, tags=tags)
        elif kind in ("o", "of"):
            cx, cy, r = prim[1] * k + x, prim[2] * k + y, prim[3] * k
            if kind == "o":
                canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=w, tags=tags)
            else:
                canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=color, tags=tags)
