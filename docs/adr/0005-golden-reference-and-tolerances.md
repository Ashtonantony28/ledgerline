# 0005: Independent Python reference model and comparison tolerances

- **Status:** Accepted
- **Date:** 2026-11-19

## Decision
- Each workbook has a reference implementation in `python/ledgerline/ref/`, written from the model spec in
  `docs/models/`, consuming the same `Inputs` as the generator and computing everything else itself.
- CI recalculates each workbook with LibreOffice headless and with the `formulas` package, then compares.
- Tolerances: currency $0.01 absolute (1e-8 in $m model units); ratios, per-share and share counts 1e-9
  relative; IRR 1e-6 absolute. Tolerances are never loosened silently; a change needs a superseding ADR.
- Before a release the workbook is recalculated in Microsoft Excel (xlwings, `tools/excel_check.py`).

## Consequences
Two engines plus Excel catch engine-specific behaviour. Function choice is limited to what all engines agree
on (ADR 0007).
