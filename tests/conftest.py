import math
import os

import pytest
from pyembroidery import COLOR_CHANGE, JUMP, STITCH, TRIM, read_dst

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">'


def skriv_svg(mapp, namn, innehall, w=100, h=100):
    sokvag = os.path.join(str(mapp), namn)
    with open(sokvag, "w") as f:
        f.write(SVG_HEAD.format(w=w, h=h) + innehall + "</svg>")
    return sokvag


@pytest.fixture
def svg_kvadrat(tmp_path):
    return skriv_svg(tmp_path, "kvadrat.svg",
                     '<rect x="25" y="25" width="50" height="50" fill="#000000"/>')


@pytest.fixture
def svg_cirkel(tmp_path):
    return skriv_svg(tmp_path, "cirkel.svg", '<circle cx="50" cy="50" r="30" fill="#cc0000"/>')


@pytest.fixture
def svg_tva_farger(tmp_path):
    return skriv_svg(tmp_path, "tva_farger.svg",
                     '<rect x="5" y="5" width="30" height="30" fill="#ff0000"/>'
                     '<rect x="55" y="55" width="30" height="30" fill="#0000ff"/>')


@pytest.fixture
def svg_lang_linje(tmp_path):
    return skriv_svg(tmp_path, "linje.svg",
                     '<path d="M 0 50 L 200 50" fill="none" stroke="#000000" stroke-width="1"/>',
                     w=200, h=100)


def las_dst(sokvag):
    """Läs tillbaka DST-filen precis som en maskin skulle få den."""
    return read_dst(sokvag)


def steg_mm(pattern):
    """Längd i mm för varje förflyttning (stygn eller hopp) i filen."""
    ut = []
    px = py = 0
    for x, y, kmd in pattern.stitches:
        kmd &= 0xFF
        if kmd in (STITCH, JUMP):
            ut.append((kmd, math.hypot(x - px, y - py) / 10.0))
        px, py = x, y
    return ut


def stygn_bbox_mm(pattern):
    xs = [x for x, y, k in pattern.stitches if (k & 0xFF) == STITCH]
    ys = [y for x, y, k in pattern.stitches if (k & 0xFF) == STITCH]
    return (max(xs) - min(xs)) / 10.0, (max(ys) - min(ys)) / 10.0
