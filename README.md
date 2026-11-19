# Ledgerline

Institutional-grade Excel financial models built on public SEC filings, where **every workbook is
re-computed by an independent Python model and CI fails on a one-cent difference**.

Excel is the deliverable. Code exists to make the Excel trustworthy: a generator writes auditable,
FAST-standard workbooks with live formulas; a reference model checks them; an audit tool scans every formula;
and a mutation test proves the checks catch injected errors.

## Workbooks

| # | Workbook | Status |
|---|---|---|
| 00 | `00_Data.xlsx`: normalised 10-K history for Costco + 7 comps, live tie-out formulas | done (M1) |
| 01 | `01_COST_ThreeStatement.xlsx`: Costco three-statement model, 3 scenarios, revolver, circuit breaker | done (M2) |
| 02 | `02_COST_Valuation.xlsx`: WACC (FRED, Damodaran, regression beta), DCF both ways, reverse DCF, comps, sensitivity grids, football field | done (M3) |
| 03 | `03_SKX_LBO.xlsx`: Skechers / 3G Capital LBO with the real financing package, sweep, PIK toggle, covenants, IRR bridge; back-test memo | done (M4) |
| 04-09 | M&A, close + consolidation, FP&A, scenario lab, dashboard, credit | M5-M10 |

## Verify

```bash
pip install -e ".[dev]"            # plus LibreOffice for headless recalculation
pytest -q                          # tie-outs; workbook vs reference on LibreOffice and `formulas`; audit
python -m ledgerline.build.workbooks                       # rebuild every workbook into workbooks/
python -m ledgerline.audit.audit workbooks/0*_*.xlsx --recalc   # writes .audit.md and .formulas.txt
python -m ledgerline.audit.mutation --n 40                 # seeded error injection, target >= 95% caught
```

Refreshing data (reviewed change): `python -m ledgerline.data.history` (set `LEDGERLINE_UA` to your own
"name contact" string per SEC fair-access policy) and `python -m ledgerline.data.prices`.

## Layout

`spec/` analyst judgement per company (drivers, rationale) · `fixtures/` committed data snapshots ·
`python/ledgerline/{data,build,models,ref,audit}` · `docs/adr/` decisions · `docs/models/` model specs ·
`workbooks/` generated files.

Educational portfolio project. Not investment advice.
