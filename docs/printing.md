# Printing the Cubepath card set

`make cards` (or `uv run cubepath-cards` from `tools/diagrams/`) writes the
set to `guide/build/cards/` and syncs it into `app/public/cards/`. Four cards:
three numbered progression cards and one annex.

| File | Use it when |
| --- | --- |
| `deck-a4-fold.pdf` | **Start here (A4).** One single-sided sheet, all four cards. Fold, glue, cut. |
| `deck-letter-fold.pdf` | Same, US Letter. |
| `deck-a4-duplex-long.pdf` | You want two-sided and your printer flips on the **long** edge. Two complete sets per sheet. |
| `deck-a4-duplex-short.pdf` | Same, but your printer flips on the **short** edge. |
| `card-N-{slug}-fold-a4.pdf` | Four copies of **one** card — wallet, desk, bag, and the one you will lose. |
| `card-N-{slug}.pdf` | Two bare 85.6 × 53.98 mm pages — for screen, or for a PVC card service. |

There is deliberately **no single duplex file that works under either flip**.
A whole-page 180° rotation on its own degenerates into a column swap, which
pairs card 1's front with card 2's back — invisible on a proof sheet of
identical cards, and wrong the moment the cards differ. Each card carries its
number on *both* faces, so a wrong flip is caught after cutting one card.

> Do **not** send a bare `card-N-{slug}.pdf` to a home printer. Chrome and most
> drivers silently shrink any PDF whose page is smaller than the paper, and you
> will get a card that is the wrong size without being told.

Every card back also carries its own **20 mm tick**, because sheet furniture
does not survive the scissors: a card cut out of a sheet can still be checked.

## The one setting that matters

Print at **100 % / Actual size**. Never "Fit to page", "Shrink oversized
pages", or "Scale to fit". Every sheet carries an 80 mm calibration bar in
both margins — measure it with a ruler after the first page. If it is not
80 mm, the scale is wrong and the card will not fit a wallet slot.

| Application | Setting |
| --- | --- |
| Acrobat / Reader | Page Sizing & Handling → Size → **Actual size**. Turn off "Auto portrait/landscape". |
| macOS Preview | **Scale: 100 %** radio button (not "Scale to Fit"). Choose A4 / US Letter, *not* the "…borderless" variant. |
| Windows / Edge | Page Sizing → **Actual size**. |
| Chrome | More settings → Scale → Custom → **100**. Its "Default" silently fits. Prefer any other viewer. |

Then check your **printer driver's own dialog** as well — a driver-level
"Fit to Paper Size" or "Reduce/Enlarge" overrides whatever the application
asked for.

## Two-sided printing

Pick the file that matches your printer's flip setting — `…-duplex-long.pdf`
for a long-edge flip, `…-duplex-short.pdf` for a short-edge one.

The grid is centred, so the cards *register* (line up edge to edge) under
either flip. What does not survive the wrong flip is **which back lands on
which front**: the two files differ by a whole-page 180° rotation, and under
the other setting that rotation reverses the row order, so card 1's front
comes out backed by the annex. The four cards are different, so this is not
the cosmetic problem it was when every card was the same.

Print **one sheet first**, cut **one** card, and check the numeral printed on
both of its faces agrees before committing paper.

## No duplex, or duplex that drifts

Home duplex typically carries 1–2 mm of registration error, which is visible
on a card this small. The fold-over PDF removes it entirely:

1. Print `cards/deck-a4-fold.pdf` **single-sided**.
2. Score the grey fold line against a ruler with the back of a knife.
3. Mountain-fold so both printed faces end up outward.
4. Glue-stick the inside, press under a book for a minute.
5. **Then** cut both layers together along the printed cut marks.

The doubled sheet is stiff and opaque, so this is also the best option if you
are not laminating.

## Paper, cutting, finishing

- **Paper:** 160–200 gsm feeds through most home printers. 200 gsm folded and
  glued gives a card that survives a pocket without lamination. Check your
  printer's maximum weight before buying heavier stock.
- **Cutting:** cut on the grey hairlines. They run the full width and height
  of the sheet, so one straight guillotine or ruler-and-knife cut serves four
  cards at once. The solid black ticks in the margins mark the same lines. On
  the fold-over sheet the crease is a *short* grey line, one card wide, and is
  the one line you never cut.
- **Corners:** an r ≈ 3 mm corner punch makes it feel like a real card.

### Lamination — an honest trade

A standard "credit card" 54 × 86 mm pouch leaves an ID-1 card about 0.4 mm of
total width clearance and effectively none in height. **It will not seal.**
You have three options:

- **Keep it wallet-sized and don't laminate.** Use the fold-over version on
  200 gsm. Recommended.
- **Laminate in a 60 × 90 mm business-card pouch**, matte rather than gloss
  (you read this under a lamp while holding a cube). The finished item is
  90 × 60 mm and **no longer fits a wallet card slot**. That is a real trade,
  not a workaround.
- **Order it properly.** Send `cards/card-0-first-solve.pdf` to a print shop as a CR80 PVC
  card: 85.6 × 53.98 mm, 0.76 mm / 30 mil. Ask them to convert RGB to CMYK.

Never trim a laminated card down to wallet size — at a 2 mm live margin, a
3 mm inset cuts into printed content on every edge.

## Black and white is fine

The card is designed to survive a mono printer:

- Chunk structure is carried by the **gap between chunks**, not by colour.
  Colour only names the trigger family, so a greyscale print loses the naming
  and no structural information.
- The OLL diagrams use a card-only print variant with a darkened mask
  (`#5F5F5F` instead of `#C0C0C0`) and thicker strokes, because yellow on
  light grey is a 1.29 : 1 contrast ratio that prints as ten identical grey
  squares.
