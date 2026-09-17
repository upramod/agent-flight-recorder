# Compiled PDF visual audit

Reviewed: 2026-09-17

Source build inspected: GitHub Actions run `35274349272`, artifact `usenix-security-2027-draft-35274349272`.

The compiled PDF was rendered page-by-page at 150 DPI and visually inspected.

## Checks

- six rendered pages present;
- two-column USENIX layout is consistent;
- title and anonymous author block render correctly;
- abstract and body text are legible;
- equations render without broken glyphs;
- architecture and experimental-flow boxes fit within columns;
- attack and utility tables fit within columns;
- section headings do not collide with body text;
- references render as normal bibliography entries;
- no clipped body text observed;
- no overlapping text observed;
- no black squares or missing-glyph boxes observed;
- no visibly broken page margins observed.

The final page contains the Open Science appendix and references and has more white space than earlier pages. This is a content-density issue, not a rendering failure. There is no need to add filler solely to consume page allowance.

## Result

Visual preflight passes. Future manuscript changes should be rebuilt and rechecked before external submission.
