"""Intern datamodell. Allt räknas i millimeter.

Ett BroderiObjekt = en form + färg + stygntyp + parametrar.
Steg 1 använder bara stygntypen "running" (löpsöm). Senare steg lägger till
t.ex. "tatami" (fyllnad) och "satin" genom att registrera fler stygngeneratorer
i brodyr/stitches/__init__.py. Själva modellen behöver då inte ändras.
"""
from dataclasses import dataclass, field

from shapely.geometry.base import BaseGeometry

Punkt = tuple[float, float]


@dataclass
class BroderiObjekt:
    geometri: BaseGeometry          # Polygon (med ev. hål) eller LineString, i mm
    farg: tuple[int, int, int]      # (R, G, B), 0-255
    stygntyp: str = "running"       # "running" nu; "tatami", "satin" senare
    parametrar: dict = field(default_factory=dict)  # t.ex. {"stygnlangd_mm": 2.5}


@dataclass
class Logga:
    objekt: list[BroderiObjekt]
    varningar: list[str] = field(default_factory=list)
    original_bredd_mm: float = 0.0   # storlek i SVG-filen före skalning
    original_hojd_mm: float = 0.0

    def farger(self) -> list[tuple[int, int, int]]:
        """Unika färger i den ordning de först förekommer."""
        sett = []
        for o in self.objekt:
            if o.farg not in sett:
                sett.append(o.farg)
        return sett

    def bbox(self):
        """(minx, miny, maxx, maxy) i mm för alla former."""
        xs0, ys0, xs1, ys1 = [], [], [], []
        for o in self.objekt:
            a, b, c, d = o.geometri.bounds
            xs0.append(a), ys0.append(b), xs1.append(c), ys1.append(d)
        return min(xs0), min(ys0), max(xs1), max(ys1)
