"""Stygngeneratorer. Varje stygntyp registreras här.

Steg 2 lägger till "tatami", steg 3 "satin" osv. genom att lägga in dem i STYGNTYPER.
En generator tar (BroderiObjekt, parametrar) och ger en lista av körningar:
    {"punkter": [(x, y), ...] i mm, "stangd": bool}
"""
from . import running

STYGNTYPER = {
    "running": running.generera,
}


def generera(objekt, parametrar=None):
    try:
        f = STYGNTYPER[objekt.stygntyp]
    except KeyError:
        raise ValueError(f"Okänd stygntyp: {objekt.stygntyp!r}")
    p = dict(objekt.parametrar)
    p.update(parametrar or {})
    return f(objekt, p)
