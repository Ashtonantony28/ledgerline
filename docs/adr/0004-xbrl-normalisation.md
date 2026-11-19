# 0004: XBRL normalisation into the Ledgerline standard chart

- **Status:** Accepted
- **Date:** 2026-11-19

## Decision
- Source: SEC EDGAR `companyfacts` JSON (us-gaap namespace; company extension tags are not exposed there).
- Only 10-K / 10-K/A facts. Flow items require an annual period of 350-380 days (admits 52/53-week years).
- Per item and period, the latest-filed value wins, so comparatives reflect restatements; each cell records
  `tag@accession`.
- A tag map (`python/ledgerline/data/tagmap.yaml`) lists candidate tags per line item in priority order, with
  `derive` formulas for missing totals and `plug` residuals so every reported subtotal ties.
- Tie-out: hard checks (A = L + E, net income attribution, CF sums to change in cash, cash roll-forward) must
  pass to $0.5m; soft checks warn on large plugs and EPS rounding.
- Modelled company keeps 10 years; comps keep 5 (older comparatives for some comps break the cash roll-forward
  after restricted-cash and discontinued-operations restatements).
- Overrides go in `fixtures/<TICKER>/overrides.yaml`, each with a citation.

## Consequences
Plugs are visible and labelled. Companies that use extension tags for major lines (e.g. Kroger's OG&A) show
large plugs; the tie-out report warns, and such comps are used only for headline multiples.
