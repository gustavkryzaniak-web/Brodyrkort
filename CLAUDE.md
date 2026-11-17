# Brodyrkort

Program som gör om vektorloggor (SVG) till brodyrfiler (DST, Tajima) för kommersiella brodyrmaskiner.
Byggs i små steg som provbroderas på riktig maskin efter varje steg. Användaren är inte utvecklare: förklara kort och enkelt.

**Läs alltid [REGELBOK.md](REGELBOK.md) innan du ändrar stygnlogik.** Ändra regeln där först, sedan i koden.

## Byggplan
1. **SVG in, DST ut, bara löpsöm längs konturerna** ← gjort, väntar på provbrodering
2. Fyllnad av ytor (tatami) med underlagsstygn
3. Satinsöm för smala former och text
4. Dragkompensation, sömnadsordning, trådklipp och färgbyten
5. Förhandsvisning och enkelt webbgränssnitt
6. Inställningar per material (piké, softshell, keps)

Lägg inte till funktioner från senare steg i förväg. Datamodellen (`brodyr/model.py`) och stygnregistret
(`brodyr/stitches/__init__.py`, `STYGNTYPER`) har plats för fler stygntyper.

## Struktur
- `brodyr/svg_import.py` – läser SVG, ger former i mm, grupperade per färg
- `brodyr/model.py` – `BroderiObjekt` (form, färg, stygntyp, parametrar) och `Logga`
- `brodyr/stitches/running.py` – löpsöm
- `brodyr/export.py` – sömnadsordning, hopp, klipp, färgbyten, låsstygn, DST
- `brodyr/preview.py` – förhandsbild (PNG) och sammanfattning
- `brodyr/cli.py` – kommandoraden
- `tools/png_till_svg.py` – hjälpverktyg som gör PNG med genomskinlig botten till SVG
- `tests/` – pytest (skapar egna SVG-filer)
- `testlogos/` – riktiga testloggor
- `output/` – genererade filer (ignoreras av git)

## Köra
Första gången (skapar virtuell miljö):
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```
Brodera en logga:
```bash
. .venv/bin/activate
python -m brodyr.cli testlogos/gotland_gokart.svg --bredd-mm 80
```
Flaggor: `--bredd-mm`, `--stygnlangd-mm`, `--ram-mm`, `--original-storlek`, `--las` (lite/normal/inget), `--ut`.
Resultatet hamnar i `output/<namn>.dst` och `output/<namn>.png`.

## Testa
```bash
. .venv/bin/activate && python -m pytest -q
```

## Git
Committa efter varje fungerande delsteg med tydligt meddelande. Utveckla på branchen som sessionen anger.
