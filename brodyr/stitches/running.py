"""Löpsöm längs konturer. Se REGELBOK.md (avsnitt Löpsöm).

generera(objekt, parametrar) -> lista av "körningar". En körning är en lista
av punkter (mm) som ska sys i följd, utan låsstygn (de läggs till i export.py).
"""
import math

from shapely.geometry import LineString, Polygon

STANDARD_STYGNLANGD_MM = 2.5
MIN_STYGN_MM = 0.3          # kortare stygn tas bort
FORENKLING_MM = 0.05        # konturen förenklas så att hörn blir tydliga
HORNVINKEL_GRADER = 35.0    # skarpare än så räknas som hörn (stygn läggs i hörnet)


def _vinkel_vid(a, b, c):
    """Riktningsändring (grader) vid b på vägen a -> b -> c."""
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def _langs_kedja(pts, langd):
    """Jämnt fördelade punkter längs polylinjen pts, högst `langd` mellan punkterna.
    Returnerar alla punkter utom startpunkten."""
    seglen = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seglen)
    if total == 0:
        return []
    n = max(1, math.ceil(total / langd - 1e-9))
    steg = total / n
    ut = []
    seg, passerat = 0, 0.0
    for k in range(1, n + 1):
        mal = k * steg
        while seg < len(seglen) - 1 and passerat + seglen[seg] < mal - 1e-12:
            passerat += seglen[seg]
            seg += 1
        t = 0.0 if seglen[seg] == 0 else (mal - passerat) / seglen[seg]
        t = min(1.0, max(0.0, t))
        a, b = pts[seg], pts[seg + 1]
        ut.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    ut[-1] = pts[-1]
    return ut


def stygn_langs(punkter, stygnlangd_mm, stangd):
    """Gör om en kontur till stygnpunkter. Hörn bevaras. Stängd kontur slutar där den började."""
    pts = list(punkter)
    if stangd and pts[0] != pts[-1]:
        pts.append(pts[0])
    simp = LineString(pts).simplify(FORENKLING_MM, preserve_topology=False)
    pts = list(simp.coords)
    if len(pts) < 2:
        return []
    # hörnindex (start och slut räknas alltid som hörn)
    horn = [0]
    for i in range(1, len(pts) - 1):
        if _vinkel_vid(pts[i - 1], pts[i], pts[i + 1]) > HORNVINKEL_GRADER:
            horn.append(i)
    horn.append(len(pts) - 1)
    ut = [pts[0]]
    for a, b in zip(horn, horn[1:]):
        ut.extend(_langs_kedja(pts[a:b + 1], stygnlangd_mm))
    return rensa_korta(ut, stangd)


def rensa_korta(pts, stangd=False):
    """Ta bort stygn kortare än MIN_STYGN_MM. Slutpunkten behålls."""
    if len(pts) < 2:
        return []
    ut = [pts[0]]
    for p in pts[1:-1]:
        if math.dist(p, ut[-1]) >= MIN_STYGN_MM:
            ut.append(p)
    sista = pts[-1]
    if math.dist(sista, ut[-1]) >= MIN_STYGN_MM:
        ut.append(sista)
    elif len(ut) > 1:
        ut[-1] = sista   # ersätt för att behålla slutpunkten (t.ex. ringens start)
    else:
        return []
    return ut


def generera(objekt, parametrar=None):
    """Löpsöm längs yttre kontur och hål (Polygon) eller längs linjen (LineString)."""
    langd = float((parametrar or {}).get("stygnlangd_mm", STANDARD_STYGNLANGD_MM))
    g = objekt.geometri
    korningar = []
    if isinstance(g, Polygon):
        ringar = [g.exterior] + list(g.interiors)
        for r in ringar:
            k = stygn_langs(list(r.coords), langd, stangd=True)
            if len(k) >= 2:
                korningar.append({"punkter": k, "stangd": True})
    elif isinstance(g, LineString):
        k = stygn_langs(list(g.coords), langd, stangd=False)
        if len(k) >= 2:
            korningar.append({"punkter": k, "stangd": g.coords[0] == g.coords[-1]})
    return korningar
