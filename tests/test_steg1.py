import glob
import os

import pytest
from pyembroidery import COLOR_CHANGE, JUMP, STITCH

from brodyr.cli import kor, main
from brodyr.svg_import import SvgFel, las_svg

from .conftest import ROT, las_dst, skriv_svg, steg_mm, stygn_bbox_mm


def test_kvadrat_50mm_blir_50mm(svg_kvadrat, tmp_path):
    dst, png, stat, text = kor(svg_kvadrat, bredd_mm=50, ut_mapp=str(tmp_path))
    b, h = stygn_bbox_mm(las_dst(dst))
    assert b == pytest.approx(50.0, abs=0.2)
    assert h == pytest.approx(50.0, abs=0.2)
    assert os.path.exists(png)


def test_kvadrat_originalstorlek_enheter(svg_kvadrat, tmp_path):
    # SVG:n är 100 mm med viewBox 100 enheter; kvadraten är 50 enheter = 50 mm.
    dst, *_ = kor(svg_kvadrat, original_storlek=True, ut_mapp=str(tmp_path))
    b, h = stygn_bbox_mm(las_dst(dst))
    assert b == pytest.approx(50.0, abs=0.2)


def test_px_ar_96_dpi(tmp_path):
    # 96 px utan enhet = 25,4 mm
    sokv = os.path.join(str(tmp_path), "px.svg")
    open(sokv, "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
                          '<rect x="10" y="10" width="96" height="96" fill="#000"/></svg>')
    logga = las_svg(sokv, None)
    x0, y0, x1, y1 = logga.bbox()
    assert x1 - x0 == pytest.approx(25.4, abs=0.01)


def test_transform_hanteras(tmp_path):
    sokv = skriv_svg(tmp_path, "t.svg", '<g transform="scale(2)"><rect x="0" y="0" width="10" height="10" fill="#000"/></g>')
    x0, y0, x1, y1 = las_svg(sokv, None).bbox()
    assert x1 - x0 == pytest.approx(20.0, abs=0.01)


def test_inget_steg_over_12_1mm(svg_kvadrat, svg_cirkel, svg_tva_farger, svg_lang_linje, tmp_path):
    for fil, kw in [(svg_kvadrat, {}), (svg_cirkel, {}), (svg_tva_farger, {"bredd_mm": 400}),
                    (svg_lang_linje, {"bredd_mm": 200}),
                    (svg_kvadrat, {"stygnlangd_mm": 30.0})]:  # extremt lång stygnlängd delas upp
        dst, *_ = kor(fil, ut_mapp=str(tmp_path), **kw)
        for kmd, mm in steg_mm(las_dst(dst)):
            assert mm <= 12.1, f"{os.path.basename(fil)} {kw}: steg på {mm:.2f} mm"


def test_lang_forflyttning_delas_i_hopp(svg_tva_farger, tmp_path):
    dst, _, stat, _ = kor(svg_tva_farger, bredd_mm=300, ram_mm=500, ut_mapp=str(tmp_path))
    steg = steg_mm(las_dst(dst))
    assert sum(1 for k, _ in steg if k == JUMP) >= 2
    assert max(mm for _, mm in steg) <= 12.1


def test_tva_farger_ger_ett_farg_byte(svg_tva_farger, tmp_path):
    dst, _, stat, _ = kor(svg_tva_farger, ut_mapp=str(tmp_path))
    p = las_dst(dst)
    assert sum(1 for s in p.stitches if (s[2] & 0xFF) == COLOR_CHANGE) == 1
    assert stat.farg_byten == 1 and stat.farger == 2


def test_nastan_lika_farger_blir_en_trad(tmp_path):
    sokv = skriv_svg(tmp_path, "svart.svg",
                     '<rect x="0" y="0" width="30" height="30" fill="#000000"/>'
                     '<rect x="60" y="60" width="30" height="30" fill="#141414"/>')
    assert len(las_svg(sokv).farger()) == 1


def test_stygn_inte_kortare_an_0_3mm(svg_cirkel, svg_kvadrat, tmp_path):
    for fil in (svg_cirkel, svg_kvadrat):
        dst, *_ = kor(fil, ut_mapp=str(tmp_path))
        for kmd, mm in steg_mm(las_dst(dst)):
            if kmd == STITCH:
                assert mm >= 0.29, f"för kort stygn {mm:.2f} mm"


def test_lasstygn_i_borjan_och_slut(svg_kvadrat, tmp_path):
    dst, *_ = kor(svg_kvadrat, ut_mapp=str(tmp_path))
    p = las_dst(dst)
    st = [(x, y) for x, y, k in p.stitches if (k & 0xFF) == STITCH]
    # tre låsstygn om 0,5 mm i början
    import math
    assert [round(math.dist(st[i], st[i + 1]) / 10, 1) for i in range(0, 2)] == [0.5, 0.5]


def test_varnar_for_stor_logga(svg_kvadrat, tmp_path):
    *_, stat, text = kor(svg_kvadrat, bredd_mm=120, ut_mapp=str(tmp_path))
    assert "större än ramen" in text
    *_, text2 = kor(svg_kvadrat, bredd_mm=120, ram_mm=150, ut_mapp=str(tmp_path))
    assert "större än ramen" not in text2


def test_varnar_for_text_och_bild(tmp_path):
    sokv = skriv_svg(tmp_path, "tb.svg",
                     '<rect width="20" height="20" fill="#000"/><text x="5" y="5">Hej</text>'
                     '<image href="data:image/png;base64,AAAA" width="10" height="10"/>')
    logga = las_svg(sokv)
    tot = " ".join(logga.varningar)
    assert "<text>" in tot and "rasterbilder" in tot


def test_bara_text_ger_tydligt_fel(tmp_path):
    sokv = skriv_svg(tmp_path, "bara_text.svg", '<text x="5" y="5">Hej</text>')
    with pytest.raises(SvgFel):
        las_svg(sokv)


def test_cli_kraschar_inte_pa_trasiga_filer(tmp_path, capsys):
    trasig = os.path.join(str(tmp_path), "trasig.svg")
    open(trasig, "w").write("det här är inte xml")
    tom = skriv_svg(tmp_path, "tom.svg", "")
    kod = main([trasig, tom, "finns_inte.svg", "--ut", str(tmp_path)])
    ut = capsys.readouterr().out
    assert kod == 1 and ut.count("FEL:") == 3


def test_alla_testlogos(tmp_path, capsys):
    filer = sorted(glob.glob(os.path.join(ROT, "testlogos", "*.svg")))
    assert filer, "inga filer i testlogos/"
    for f in filer:
        main([f, "--ut", str(tmp_path)])  # får varna, men inte krascha
        dst = os.path.join(str(tmp_path), os.path.splitext(os.path.basename(f))[0] + ".dst")
        if os.path.exists(dst):
            for kmd, mm in steg_mm(las_dst(dst)):
                assert mm <= 12.1
    ut = capsys.readouterr().out
    assert "Oväntat fel" not in ut


def test_cirkel_ar_slutna_konturer(svg_cirkel, tmp_path):
    dst, _, stat, _ = kor(svg_cirkel, bredd_mm=60, ut_mapp=str(tmp_path))
    b, h = stygn_bbox_mm(las_dst(dst))
    assert b == pytest.approx(60, abs=0.5) and h == pytest.approx(60, abs=0.5)
    assert stat.klipp == 1 and stat.hopp >= 1  # ett klipp före återgången till origo


def test_filen_slutar_i_origo(svg_kvadrat, tmp_path):
    dst, *_ = kor(svg_kvadrat, ut_mapp=str(tmp_path))
    p = las_dst(dst)
    x, y, k = p.stitches[-1]
    assert (x, y) == (0, 0)
