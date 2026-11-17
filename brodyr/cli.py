"""Kommandoraden.

Exempel:
    python -m brodyr.cli testlogos/gotland_gokart.svg --bredd-mm 80
"""
import argparse
import os
import sys

from .export import bygg_monster, skriv_dst
from .preview import skriv_png, sammanfattning
from .svg_import import SvgFel, las_svg


def kor(svg_fil, bredd_mm=80.0, stygnlangd_mm=2.5, ram_mm=100.0, ut_mapp="output", original_storlek=False, las="lite", filnamn=None):
    namn = filnamn or os.path.splitext(os.path.basename(svg_fil))[0]
    logga = las_svg(svg_fil, None if original_storlek else bredd_mm)
    pattern, stat = bygg_monster(logga, stygnlangd_mm, namn, las)

    # Ramvarning på det som faktiskt broderas (stygnens utsträckning)
    if stat.bredd_mm > ram_mm or stat.hojd_mm > ram_mm:
        stat.varningar.append(
            f"Loggan ({stat.bredd_mm:.1f} x {stat.hojd_mm:.1f} mm) är större än ramen "
            f"{ram_mm:g} x {ram_mm:g} mm. Minska --bredd-mm eller använd en större ram (--ram-mm).")

    dst = os.path.join(ut_mapp, namn + ".dst")
    png = os.path.join(ut_mapp, namn + ".png")
    skriv_dst(pattern, dst)
    skriv_png(pattern, logga.farger(), png, (ram_mm, ram_mm))
    text = sammanfattning(namn, stat, (logga.original_bredd_mm, logga.original_hojd_mm), (ram_mm, ram_mm))
    return dst, png, stat, text


def main(argv=None):
    ap = argparse.ArgumentParser(prog="brodyr", description="Gör om en SVG-logga till en DST-brodyrfil (löpsöm).")
    ap.add_argument("svg", nargs="+", help="SVG-fil(er)")
    ap.add_argument("--bredd-mm", type=float, default=80.0, help="loggans bredd i mm (standard 80)")
    ap.add_argument("--original-storlek", action="store_true", help="behåll SVG-filens egen storlek")
    ap.add_argument("--stygnlangd-mm", type=float, default=2.5, help="löpsömmens stygnlängd (standard 2,5)")
    ap.add_argument("--ram-mm", type=float, default=100.0, help="ramens sida i mm (standard 100)")
    ap.add_argument("--las", choices=["lite", "normal", "inget"], default="lite",
                    help="låsstygn: lite (standard, minst knut), normal (3 stygn), inget")
    ap.add_argument("--ut", default="output", help="mapp för resultatet (standard output)")
    a = ap.parse_args(argv)

    fel = 0
    for fil in a.svg:
        try:
            dst, png, stat, text = kor(fil, a.bredd_mm, a.stygnlangd_mm, a.ram_mm, a.ut, a.original_storlek, a.las)
            print(text)
            print(f"Skrev {dst} och {png}\n")
        except SvgFel as e:
            fel += 1
            print(f"=== {os.path.basename(fil)} ===\nFEL: {e}\n")
        except FileNotFoundError:
            fel += 1
            print(f"=== {os.path.basename(fil)} ===\nFEL: Filen hittades inte.\n")
        except Exception as e:  # sista skyddsnät: aldrig en oförklarad krasch
            fel += 1
            print(f"=== {os.path.basename(fil)} ===\nFEL: Oväntat fel ({type(e).__name__}: {e}).\n")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
