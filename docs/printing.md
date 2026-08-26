# Printing the cheat card

`make cheatcards` (or `uv run cubepath-cheatcards` from `tools/diagrams/`)
writes five PDFs to `guide/build/`. Pick the one that matches your printer —
they are not interchangeable.

| File | Use it when |
| --- | --- |
| `cheat-card-a4.pdf` | **Start here (A4).** Two-sided, 8 cards per sheet. |
| `cheat-card-letter.pdf` | Same, US Letter. |
| `cheat-card-a4-fold.pdf` | Your printer has **no duplex**, or your duplex misaligns. 4 cards per sheet. |
| `cheat-card-letter-fold.pdf` | Same, US Letter. |
| `cheat-card.pdf` | Two bare 85.6 × 53.98 mm pages — for reading on screen, or for a print shop. |

> Do **not** send `cheat-card.pdf` to a home printer. Chrome and most drivers
> silently shrink any PDF whose page is smaller than the paper, and you will
> get a card that is the wrong size without being told.

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

Choose **two-sided, flip on LONG edge** (portrait).

The card grid is centred on the sheet and every card on a side is identical,
so the layout is symmetric under both the long-edge mirror and the short-edge
mirror. Fronts and backs therefore register under **either** duplex setting —
if the backs come out upside down, switch to short edge and the cards still
line up.

Print **one sheet first** and hold it up to a light before committing paper.

## No duplex, or duplex that drifts

Home duplex typically carries 1–2 mm of registration error, which is visible
on a card this small. The fold-over PDF removes it entirely:

1. Print `cheat-card-a4-fold.pdf` **single-sided**.
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
  cards at once. The solid black ticks in the margins mark the same lines.
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
- **Order it properly.** Send `cheat-card.pdf` to a print shop as a CR80 PVC
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
