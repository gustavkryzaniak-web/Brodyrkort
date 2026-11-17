# REGELBOK – brodyrregler och parametrar

Alla regler för stygnlogiken står här, med motivering. Läs den **innan** du ändrar något som påverkar stygn.
Den växer när vi lär oss av provbroderingar. Ändra en regel här först, sedan i koden.

Kolumnen "Provbroderat" fylls i efter varje provsömnad (datum, maskin, material, resultat).

## Maskin

- **Tajima, 6 huvuden.** Läser DST direkt. Samma mönster sys på alla huvuden, så loggan måste få plats i ramen på varje huvud.
- Modell, ramstorlekar, maximal sömnadshastighet och om man broderar plagg eller kepsar är inte kända ännu. Fyll i här efter första provbroderingen.
- Trådklipp skrivs som tre små hopp i DST (`trim_at=3`). Det är så Tajima-maskiner normalt tolkar ett klipp, men det ska bekräftas i provbroderingen.
- Hastighet: sytiden i sammanfattningen räknas med 800 stygn/min. Justera när vi vet vad maskinen går i verkligheten.

## Referensfil från riktig produktion

`Katthammarsvik_230013.DST` (från er egen programvara) analyserad:

| Mått | Värde |
|---|---|
| Storlek | 90,0 x 66,5 mm |
| Antal stygn | 8 775 (en färg, inga färgbyten) |
| Trådklipp / hopp | 11 klipp, 35 hopp, 9 sömnadssekvenser |
| Stygnlängd | median 1,3 mm, medel 1,4 mm, längsta 9,6 mm. 79 % ligger mellan 1,0 och 2,5 mm. 0,6 % är kortare än 0,3 mm (kortast 0,2 mm) |
| Låsstygn | Tre lägen (`--las`): **lite** (standard sedan test 1): start = 2 stygn om 0,8 mm längs sömmen, slut = 1 stygn 0,8 mm bakåt längs sömmen. **normal** (test 1): 3 + 3 stygn om 0,5 mm. **inget**: inga lås. | Test 1 (normal) gav en liten synlig knut vid varje trådklipp. Orsak: för många trådlager på 0,5 mm, och på slutna konturer ligger start- och slutlås på samma ställe (6 extra stygn). Lite lås sprider ut låsen (start 0,8 mm framåt, slut 0,8 mm bakåt) och ger färre lager. | Test 1 (normal): knut synlig på framsidan. Test 2: väntar (lite / inget). |
| Klipp | Klipp läggs efter låsstygn. Klipp + hopp används även för korta flyttar (cirka 2 mm). |
| Start och slut | Börjar med hopp från origo och slutar med klipp, hopp tillbaka till origo, END |

Slutsatser: våra löpsömsstygn (2,5 mm) är längre än referensens fyllnads-/satinstygn. Fyllnad i steg 2 bör ligga kring 1,0–2,5 mm stygnlängd. En logga i den här storleken blir flera tusen stygn, så sytiden blir betydligt längre än våra 0,7 minuter för bara konturer.

## Enheter och format

| Regel | Värde | Motivering | Provbroderat |
|---|---|---|---|
| Enhet i DST/pyembroidery | 0,1 mm | DST-formatet räknar i tiondels millimeter. Internt räknar vi i mm och avrundar till heltal först när kommandot skrivs. | – |
| px i SVG | 96 dpi (1 px = 0,2646 mm) | SVG-standarden. | – |
| Koordinatsystem | x åt höger, y nedåt (som i SVG och pyembroidery) | pyembroidery vänder y själv när DST skrivs. | – |
| Loggans läge | Centrerad kring origo (0,0) | Maskinen börjar i ramens mitt. | – |
| Standardbredd | 80 mm (`--bredd-mm`) | Typisk loggabredd på bröst/keps. | – |
| Ram | 100 x 100 mm (`--ram-mm`) | Varning om loggan (stygnens utsträckning) är större. | – |

## Löpsöm (steg 1)

| Regel | Värde | Motivering | Provbroderat |
|---|---|---|---|
| Stygnlängd | 2,5 mm (`--stygnlangd-mm`) | Vanligt värde för löpsöm. Kortare ger många stygn, längre ser kantigt ut. | – |
| Hörn | Stygn läggs alltid i hörn (riktningsändring > 35°) | Annars skärs hörn av och bokstäver blir runda. Kurvor delas jämnt. | – |
| Konturförenkling | 0,05 mm | Tar bort brus från SVG-kurvor så att hörn kan hittas. | – |
| Kontur | Yttre kontur och alla hål | Steg 1 broderar bara linjer. Hål är egna slutna konturer. | – |
| Slutna konturer | Börjar och slutar i samma punkt | Ger stängd form utan glapp. Startpunkten väljs nära där tråden redan är. | – |
| Kortaste stygn | 0,3 mm | Kortare stygn kan få tråden att gå av. Tas bort (slutpunkten behålls). | – |
| Längsta stygn / hopp | 12,1 mm är maskinens gräns. Vi delar redan över 12,0 mm i bitar om högst 11,0 mm | Marginal för avrundning till 0,1 mm. DST kan inte koda mer än 12,1 mm per rad. | – |
| Låsstygn | 3 stygn om 0,5 mm (fram, tillbaka, fram) i början och slutet av varje sömnadssekvens | Så att tråden inte släpper efter klipp. | – |

## Hopp, trådklipp och sömnadsordning

| Regel | Värde | Motivering | Provbroderat |
|---|---|---|---|
| Ordning inom en färg | Närmaste nästa form (och närmaste kontur i en form) | Minskar hopp och trådklipp. Enkel girig metod, inte optimal. | – |
| Avstånd mellan former ≤ 2 mm | Sy direkt, inga låsstygn, inget klipp | Trådsvansen syns inte, sparar klipp. | – |
| Avstånd > 2 mm | Låsstygn, TRIM (trådklipp), JUMP | Annars syns en tråd tvärs över loggan. | – |
| Hopp längre än gränsen | Delas i flera JUMP | DST-gräns. | – |
| TRIM i DST | pyembroidery skriver TRIM som tre små hopp (standard `trim_at=3`) | Det är så DST-maskiner känner igen ett klipp. Kan variera mellan maskinmärken. | – |
| Färgbyte | COLOR_CHANGE mellan färger, END sist | Maskinen klipper själv vid färgbyte. Inget extra TRIM läggs in. | – |
| Slutposition | Sista sömnadssekvensen får låsstygn och klipp, därefter hopp tillbaka till origo (0,0) och END | Så gör referensfilen från er egen programvara (Katthammarsvik). Maskinen står då i ramens mitt. | – |

## Färger

| Regel | Värde | Motivering | Provbroderat |
|---|---|---|---|
| Färggruppering | Fyllnadsfärg, annars streckfärg | Löpsöm följer formen, så färgen tas från formens färg. | – |
| Nästan lika färger | RGB-avstånd < 48 räknas som samma tråd (första färgen vinner) | Olika svarta nyanser från grafikprogram ska inte ge extra färgbyten. | – |
| Färgordning | Den ordning färgerna först förekommer i SVG-filen | Bakifrån och fram, som i designen. Steg 4 gör en riktig sömnadsordning. | – |

## SVG-import

| Regel | Beskrivning |
|---|---|
| Text | `<text>` kan inte broderas. Varning, texten hoppas över. Gör om till banor i Inkscape (Bana > Objekt till bana) eller Illustrator (Skriv > Skapa konturer). |
| Rasterbilder | `<image>` kan inte broderas. Varning, bilden hoppas över. Vektorisera först. |
| Osynliga och färglösa former | Hoppas över (`display:none`, `fill:none` utan streck). |
| Hål | Jämn-udda-regeln (evenodd): överlappande delar av samma bana blir hål. Nonzero-fyllning med överlapp tolkas alltså inte exakt. |
| Streck utan fyllnad | Löpsöm längs själva linjen (öppen eller sluten). Strecktjocklek ignoreras i steg 1. |
| Kurvor | Delas i bitar om högst 0,15 mm innan stygnen läggs. |
| Skräpformer | Ytor under 0,01 mm² ignoreras. |

## Att lära från provbroderingar

Fyll i här efter varje provsömnad: datum, maskin, material, tråd, vad som blev bra/dåligt och vilken regel som ändras.

- **Test 1** (Tajima 6 huvuden, steg 1, 80 mm, lås *normal*): rätt bredd och höjd, stygnen på rätt plats. Fel: liten knut på framsidan vid varje trådklipp (låsstygnen syns eftersom konturen ligger ytligt och slutna konturer får lås i både start och slut på samma ställe). Åtgärd: nytt standardläge `--las lite`, plus `--las inget` att jämföra med.
