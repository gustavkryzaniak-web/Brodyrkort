"""Förhandsbild (PNG) och sammanfattning i text."""
from PIL import Image, ImageDraw
from pyembroidery import COLOR_CHANGE, JUMP, STITCH, TRIM

from .export import ENH_PER_MM, Statistik


def _ljus(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def skriv_png(pattern, farger, sokvag, ram_mm=(100.0, 100.0), px_per_mm=10):
    """Ritar stygnen i trådfärgerna. Hopp ritas som tunna röda linjer, trådklipp som små ringar.
    Är alla trådar ljusa används mörk bakgrund så att man ser något. Streckad ruta = ramen."""
    bred = max(100.0, ram_mm[0] * 1.2)
    hog = max(100.0, ram_mm[1] * 1.2)
    # bounds i mm
    pts = [(s[0] / ENH_PER_MM, s[1] / ENH_PER_MM) for s in pattern.stitches]
    if pts:
        mx = max(abs(p[0]) for p in pts) * 2 + 10
        my = max(abs(p[1]) for p in pts) * 2 + 10
        bred, hog = max(bred, mx), max(hog, my)
    W, H = int(bred * px_per_mm), int(hog * px_per_mm)
    mork = bool(farger) and all(_ljus(c) > 170 for c in farger)
    bg = (38, 38, 42) if mork else (255, 255, 255)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    def pp(x, y):
        return (W / 2 + x / ENH_PER_MM * px_per_mm, H / 2 + y / ENH_PER_MM * px_per_mm)

    # ram + korshår
    ramfarg = (110, 110, 120) if mork else (170, 170, 180)
    rx, ry = ram_mm[0] / 2 * px_per_mm, ram_mm[1] / 2 * px_per_mm
    d.rectangle([W / 2 - rx, H / 2 - ry, W / 2 + rx, H / 2 + ry], outline=ramfarg, width=2)
    d.line([W / 2 - 15, H / 2, W / 2 + 15, H / 2], fill=ramfarg, width=1)
    d.line([W / 2, H / 2 - 15, W / 2, H / 2 + 15], fill=ramfarg, width=1)

    fi = 0
    cur = (0, 0)
    for x, y, kmd in pattern.stitches:
        kmd &= 0xFF
        farg = farger[min(fi, len(farger) - 1)] if farger else (0, 0, 0)
        if kmd == STITCH:
            d.line([pp(*cur), pp(x, y)], fill=tuple(farg), width=3)
        elif kmd == JUMP:
            d.line([pp(*cur), pp(x, y)], fill=(230, 60, 60), width=1)
        elif kmd == TRIM:
            a, b = pp(x, y)
            d.ellipse([a - 6, b - 6, a + 6, b + 6], outline=(240, 170, 40), width=2)
        elif kmd == COLOR_CHANGE:
            fi += 1
        cur = (x, y)
    # beskär till innehåll + marginal (men visa alltid hela ramen)
    img.save(sokvag)


def sammanfattning(namn, stat: Statistik, orig_mm=None, ram_mm=(100.0, 100.0)) -> str:
    rader = [f"=== {namn} ==="]
    if orig_mm:
        rader.append(f"Storlek i SVG-filen:  {orig_mm[0]:.1f} x {orig_mm[1]:.1f} mm")
    rader += [
        f"Broderistorlek:       {stat.bredd_mm:.1f} x {stat.hojd_mm:.1f} mm",
        f"Antal stygn:          {stat.stygn}",
        f"Antal färger:         {stat.farger}",
        f"Antal trådklipp:      {stat.klipp}",
        f"Antal hopp:           {stat.hopp}",
        f"Längsta stygn/hopp:   {stat.langsta_steg_mm:.1f} mm",
        f"Uppskattad sytid:     {stat.sytid_min:.1f} min (vid 800 stygn/min)",
    ]
    for v in stat.varningar:
        rader.append(f"VARNING: {v}")
    return "\n".join(rader)
