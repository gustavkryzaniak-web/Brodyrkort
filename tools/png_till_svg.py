"""Hjälpverktyg: gör om en PNG (med genomskinlig bakgrund) till en enkel SVG.

Användning:
    python tools/png_till_svg.py in.png ut.svg [--farg "#ffffff"] [--min-area 150]

Formen tas från PNG-filens alfakanal (det som inte är genomskinligt).
Små fläckar under --min-area (pixlar²) tas bort så att damm och suddiga
streck inte blir tusentals onödiga stygn.
"""
import argparse

import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from skimage import measure


def ring_area(pts):
    x, y = pts[:, 1], pts[:, 0]
    return 0.5 * (np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inn")
    ap.add_argument("ut")
    ap.add_argument("--farg", default="#ffffff")
    ap.add_argument("--min-area", type=float, default=150.0)
    ap.add_argument("--tolerans", type=float, default=0.8, help="förenkling i pixlar")
    a = ap.parse_args()

    im = Image.open(a.inn).convert("RGBA")
    w, h = im.size
    alpha = np.array(im)[..., 3].astype(float) / 255.0
    alpha = np.pad(alpha, 1)  # så att former vid kanten blir stängda
    contours = measure.find_contours(alpha, 0.5)

    rings = []
    for c in contours:
        c = c - 1  # ta bort paddingen
        if len(c) < 4:
            continue
        poly = Polygon(np.c_[c[:, 1], c[:, 0]])
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        simp = poly.simplify(a.tolerans)
        if simp.is_empty or simp.geom_type != "Polygon":
            continue
        if simp.area < a.min_area:
            continue
        rings.append(list(simp.exterior.coords)[:-1])

    d = " ".join(
        "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in r) + " Z" for r in rings
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">\n'
        f'  <path fill="{a.farg}" fill-rule="evenodd" d="{d}"/>\n</svg>\n'
    )
    open(a.ut, "w").write(svg)
    print(f"{len(rings)} konturer skrivna till {a.ut}")


if __name__ == "__main__":
    main()
