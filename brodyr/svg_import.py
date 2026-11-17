"""Läser en SVG-fil och ger former i millimeter, grupperade per färg.

- viewBox, width/height, enheter och transformer hanteras av svgelements.
- px räknas som 96 dpi (1 px = 25,4 / 96 mm).
- Loggan skalas proportionerligt till önskad bredd och centreras kring origo.
- Fyllnadsfärg används i första hand, annars streckfärg.
- Färger som ligger mycket nära varandra räknas som samma tråd.
"""
import math

from shapely.geometry import LineString, Polygon
from svgelements import (SVG, Close, Color, Image, Matrix, Move, Path, Shape,
                         SVGText)

from .model import BroderiObjekt, Logga

MM_PER_PX = 25.4 / 96.0
FARG_TOLERANS = 48.0   # RGB-avstånd under vilket två färger räknas som samma tråd
FLATTEN_MM = 0.15      # kurvor delas i bitar om högst så här många mm
MIN_YTA_MM2 = 0.01     # skräpformer som är mindre än så ignoreras


class SvgFel(Exception):
    """Fel som ska förklaras för användaren (ingen krasch)."""


def _rgb(c: Color):
    """Färg -> (R,G,B), eller None om 'ingen färg' / genomskinlig."""
    if c is None or c.value is None:
        return None
    if c.alpha is not None and c.alpha == 0:
        return None
    return (int(c.red), int(c.green), int(c.blue))


def _avstand(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _slå_ihop_farger(objekt: list[BroderiObjekt]):
    """Ersätt nästan-lika färger med den första färgen i gruppen."""
    reps: list[tuple[int, int, int]] = []
    for o in objekt:
        for r in reps:
            if _avstand(o.farg, r) < FARG_TOLERANS:
                o.farg = r
                break
        else:
            reps.append(o.farg)


def _flatten(path: Path, steg_px: float):
    """Path -> lista av (punkter, stängd). Punkter i px."""
    delar = []
    for sub in path.as_subpaths():
        sub = Path(sub)
        pts = []
        stangd = False
        for seg in sub:
            if isinstance(seg, Move):
                if seg.end is not None:
                    pts.append((seg.end.x, seg.end.y))
            elif isinstance(seg, Close):
                stangd = True
                if seg.end is not None:
                    pts.append((seg.end.x, seg.end.y))
            elif seg.end is None:
                continue
            elif type(seg).__name__ == "Line":
                pts.append((seg.end.x, seg.end.y))
            else:
                try:
                    n = max(4, math.ceil(seg.length() / steg_px))
                except Exception:
                    n = 16
                n = min(n, 2000)
                for i in range(1, n + 1):
                    p = seg.point(i / n)
                    pts.append((p.x, p.y))
        if len(pts) >= 2:
            if not stangd and math.dist(pts[0], pts[-1]) < 1e-6:
                stangd = True
            delar.append((pts, stangd))
    return delar


def las_svg(sokvag: str, bredd_mm: float | None = 80.0) -> Logga:
    """Läs SVG och returnera en Logga i millimeter.

    bredd_mm=None betyder att originalstorleken behålls.
    """
    varningar: list[str] = []
    try:
        svg = SVG.parse(sokvag, reify=True, ppi=96.0)
    except Exception as e:  # trasig XML, fil saknas osv.
        raise SvgFel(f"Kunde inte läsa SVG-filen '{sokvag}': {e}") from e

    har_text = har_bild = False
    former = []  # (Path i px, fyllfärg, streckfärg)
    for el in svg.elements():
        if isinstance(el, SVGText):
            har_text = True
            continue
        if isinstance(el, Image):
            har_bild = True
            continue
        if not isinstance(el, Shape):
            continue
        vals = getattr(el, "values", {}) or {}
        if str(vals.get("display", "")).strip() == "none" or \
                str(vals.get("visibility", "")).strip() in ("hidden", "collapse"):
            continue
        try:
            p = abs(Path(el))
        except Exception:
            varningar.append(f"Ett element av typen {type(el).__name__} kunde inte tolkas och hoppades över.")
            continue
        fyll = _rgb(el.fill)
        streck = _rgb(el.stroke)
        if fyll is None and streck is None:
            continue
        former.append((p, fyll, streck))

    if har_text:
        varningar.append(
            "SVG-filen innehåller <text>-element. Text kan inte broderas som text: gör om den "
            "till banor (paths) i Inkscape (Bana > Objekt till bana) eller Illustrator "
            "(Skriv > Skapa konturer) och försök igen. Texten hoppades över.")
    if har_bild:
        varningar.append(
            "SVG-filen innehåller rasterbilder (<image>). De kan inte broderas utan måste "
            "vektoriseras först. Bilderna hoppades över.")

    if not former:
        raise SvgFel("Hittade inga former att brodera i SVG-filen (bara text, bilder eller "
                     "osynliga element?). Gör om allt till banor (paths) med färg.")

    # Gemensam ruta i px
    boxar = [p.bbox() for p, _, _ in former if p.bbox() is not None]
    if not boxar:
        raise SvgFel("Formerna i SVG-filen har ingen storlek.")
    x0 = min(b[0] for b in boxar); y0 = min(b[1] for b in boxar)
    x1 = max(b[2] for b in boxar); y1 = max(b[3] for b in boxar)
    bredd_px, hojd_px = x1 - x0, y1 - y0
    if bredd_px <= 0 and hojd_px <= 0:
        raise SvgFel("Loggan har noll storlek.")

    orig_b = bredd_px * MM_PER_PX
    orig_h = hojd_px * MM_PER_PX
    if bredd_mm is None or bredd_px <= 0:
        skala = MM_PER_PX
    else:
        skala = bredd_mm / bredd_px  # mm per px
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def till_mm(pts):
        return [((x - cx) * skala, (y - cy) * skala) for x, y in pts]

    objekt: list[BroderiObjekt] = []
    for p, fyll, streck in former:
        steg_px = FLATTEN_MM / skala
        delar = _flatten(p, steg_px)
        if fyll is not None:
            geom = None
            for pts, _ in delar:
                pm = till_mm(pts)
                if len(pm) < 3:
                    continue
                poly = Polygon(pm)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
                geom = poly if geom is None else geom.symmetric_difference(poly)  # jämn-udda-regeln
            if geom is not None and not geom.is_empty:
                polys = [geom] if geom.geom_type == "Polygon" else [
                    g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
                for g in polys:
                    if g.area >= MIN_YTA_MM2:
                        objekt.append(BroderiObjekt(g, fyll))
        else:
            for pts, stangd in delar:
                pm = till_mm(pts)
                if stangd and pm[0] != pm[-1]:
                    pm.append(pm[0])
                ls = LineString(pm)
                if ls.length > 0:
                    objekt.append(BroderiObjekt(ls, streck))

    if not objekt:
        raise SvgFel("Inga broderbara former hittades efter tolkning av SVG-filen.")

    _slå_ihop_farger(objekt)
    logga = Logga(objekt, varningar, orig_b, orig_h)
    return logga
