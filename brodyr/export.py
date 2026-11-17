"""Bygger brodyrmönstret (sömnadsordning, hopp, trådklipp, färgbyten, låsstygn) och skriver DST.

Allt räknas internt i mm och omvandlas till DST-enheter (0,1 mm) först när
kommandona läggs in. Se REGELBOK.md för reglerna.
"""
import math
import os
import re
from dataclasses import dataclass, field

from pyembroidery import (COLOR_CHANGE, END, JUMP, STITCH, TRIM, EmbPattern,
                          EmbThread, write_dst)

from .model import Logga
from .stitches import generera

ENH_PER_MM = 10               # DST/pyembroidery räknar i 0,1 mm
MAX_STEG_ENH = 120            # inget enskilt stygn/hopp får överstiga 12,0 mm (gränsen är 12,1)
DELAT_STEG_ENH = 110          # längre förflyttningar delas i bitar om högst 11,0 mm
HOPPGRANS_MM = 2.0            # glesare än så: trådklipp + hopp. Närmare: sy direkt.
LASSTYGN_MM = 0.5             # låsstygnens längd
SYTAKT = 800                  # stygn per minut för sytidsuppskattning


@dataclass
class Statistik:
    bredd_mm: float = 0.0
    hojd_mm: float = 0.0
    stygn: int = 0
    hopp: int = 0
    farger: int = 0
    klipp: int = 0
    farg_byten: int = 0
    langsta_steg_mm: float = 0.0
    sytid_min: float = 0.0
    varningar: list = field(default_factory=list)


class _Byggare:
    """Lägger in kommandon i DST-enheter och delar upp för långa steg."""

    def __init__(self):
        self.kmd = []   # (kommando, x_enh, y_enh)
        self.x = 0
        self.y = 0

    @property
    def pos_mm(self):
        return (self.x / ENH_PER_MM, self.y / ENH_PER_MM)

    def _flytta(self, kommando, mx, my):
        tx, ty = round(mx * ENH_PER_MM), round(my * ENH_PER_MM)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        n = 1 if dist <= MAX_STEG_ENH else math.ceil(dist / DELAT_STEG_ENH)
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            self.x = round(x0 + dx * i / n)
            self.y = round(y0 + dy * i / n)
            self.kmd.append((kommando, self.x, self.y))

    def stygn(self, p):
        self._flytta(STITCH, *p)

    def hopp(self, p):
        self._flytta(JUMP, *p)

    def klipp(self):
        self.kmd.append((TRIM, self.x, self.y))

    def farg_byte(self):
        self.kmd.append((COLOR_CHANGE, self.x, self.y))

    def slut(self):
        self.kmd.append((END, self.x, self.y))


def _enhet(a, b):
    d = math.dist(a, b)
    if d == 0:
        return (1.0, 0.0)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def _startlas(b, p0, p1):
    """Låsstygn i början: fram och tillbaka längs sömmen (3 stygn)."""
    ux, uy = _enhet(p0, p1)
    l = min(LASSTYGN_MM, 0.8 * math.dist(p0, p1)) if math.dist(p0, p1) > 0 else LASSTYGN_MM
    l = max(l, 0.3)
    q = (p0[0] + ux * l, p0[1] + uy * l)
    b.stygn(q); b.stygn(p0); b.stygn(q)


def _slutlas(b, pn, pforegaende):
    """Låsstygn i slutet: fram och tillbaka längs sömmen bakåt (3 stygn)."""
    ux, uy = _enhet(pn, pforegaende)
    d = math.dist(pn, pforegaende)
    l = max(0.3, min(LASSTYGN_MM, 0.8 * d)) if d > 0 else LASSTYGN_MM
    q = (pn[0] + ux * l, pn[1] + uy * l)
    b.stygn(q); b.stygn(pn); b.stygn(q)


def _orientera(korning, pos):
    """Välj startpunkt/riktning så att körningen börjar nära `pos`."""
    pts = korning["punkter"]
    if korning["stangd"] and len(pts) > 2:
        ring = pts[:-1]
        i = min(range(len(ring)), key=lambda k: math.dist(ring[k], pos))
        rot = ring[i:] + ring[:i]
        return rot + [rot[0]]
    if math.dist(pts[-1], pos) < math.dist(pts[0], pos):
        return list(reversed(pts))
    return list(pts)


def _min_avstand(korningar, pos):
    return min(math.dist(p, pos) for k in korningar for p in k["punkter"])


def _ordna_farg(objekt_korningar, pos):
    """Närmaste-nästa-form. Returnerar körningar i sömnadsordning (redan orienterade)."""
    kvar = [k for k in objekt_korningar if k]
    ut = []
    while kvar:
        obj = min(kvar, key=lambda ks: _min_avstand(ks, pos))
        kvar.remove(obj)
        rest = list(obj)
        while rest:
            k = min(rest, key=lambda k: _min_avstand([k], pos))
            rest.remove(k)
            pts = _orientera(k, pos)
            ut.append(pts)
            pos = pts[-1]
    return ut


def bygg_monster(logga: Logga, stygnlangd_mm: float = 2.5, namn: str = "logga"):
    """Returnerar (EmbPattern, Statistik)."""
    stat = Statistik(varningar=list(logga.varningar))
    if stygnlangd_mm > 11.0:
        stat.varningar.append(
            f"Stygnlängden {stygnlangd_mm} mm är för lång. Max 12,1 mm tillåts; långa stygn delas upp.")
    if stygnlangd_mm < 0.5:
        stat.varningar.append(f"Stygnlängden {stygnlangd_mm} mm är mycket kort och ger onödigt många stygn.")

    farger = logga.farger()
    b = _Byggare()
    for fi, farg in enumerate(farger):
        grupp = [o for o in logga.objekt if o.farg == farg]
        korningar = [generera(o, {"stygnlangd_mm": stygnlangd_mm}) for o in grupp]
        ordning = _ordna_farg(korningar, b.pos_mm)
        if not ordning:
            continue
        if fi > 0 and b.kmd:
            b.farg_byte()
        for i, pts in enumerate(ordning):
            gap = math.dist(b.pos_mm, pts[0])
            if i > 0 and gap <= HOPPGRANS_MM:
                if gap >= 0.3:
                    b.stygn(pts[0])         # nära: sy direkt, inga lås
            else:
                b.hopp(pts[0])              # hopp (föregående körning har redan fått slutlås och klipp)
                _startlas(b, pts[0], pts[1])
            for p in pts[1:]:
                b.stygn(p)
            # Behöver körningen slutlås + klipp? Ja om nästa körning ligger långt bort eller är sist.
            nasta_nara = i + 1 < len(ordning) and math.dist(b.pos_mm, ordning[i + 1][0]) <= HOPPGRANS_MM
            if not nasta_nara:
                _slutlas(b, pts[-1], pts[-2])
                if i + 1 < len(ordning):
                    b.klipp()
    # Som i referensfilen: klipp, hoppa tillbaka till origo (ramens mitt) och avsluta.
    if b.kmd:
        b.klipp()
        b.hopp((0.0, 0.0))
    b.slut()

    pattern = EmbPattern()
    for r, g, bl in farger:
        t = EmbThread()
        t.set_color(r, g, bl)
        pattern.add_thread(t)
    pattern.metadata("name", re.sub(r"[^A-Za-z0-9_-]", "", namn)[:16] or "logga")
    for kmd, x, y in b.kmd:
        pattern.add_stitch_absolute(kmd, x, y)

    # Statistik
    px, py, langsta = 0, 0, 0.0
    xs, ys = [], []
    for kmd, x, y in b.kmd:
        steg = math.hypot(x - px, y - py) / ENH_PER_MM
        if kmd in (STITCH, JUMP):
            langsta = max(langsta, steg)
        if kmd == STITCH:
            stat.stygn += 1
            xs.append(x); ys.append(y)
        elif kmd == JUMP:
            stat.hopp += 1
        elif kmd == TRIM:
            stat.klipp += 1
        elif kmd == COLOR_CHANGE:
            stat.farg_byten += 1
        px, py = x, y
    stat.farger = stat.farg_byten + 1 if stat.stygn else 0
    if xs:
        stat.bredd_mm = (max(xs) - min(xs)) / ENH_PER_MM
        stat.hojd_mm = (max(ys) - min(ys)) / ENH_PER_MM
    stat.langsta_steg_mm = langsta
    stat.sytid_min = stat.stygn / SYTAKT
    return pattern, stat


def skriv_dst(pattern: EmbPattern, sokvag: str):
    os.makedirs(os.path.dirname(os.path.abspath(sokvag)), exist_ok=True)
    write_dst(pattern, sokvag)
