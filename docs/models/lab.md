# Model spec: scenario and sensitivity lab (workbook 07, Costco valuation)

Reference: `ref/lab.py` on top of `ref/three_statement.py` and `ref/dcf.py`. Inputs: `spec/COST.yaml` (operating
cases), `spec/LAB_COST.yaml` (flexed drivers, step sizes with rationale, stress cases, Monte Carlo settings).

## Shifts
Seven drivers can be shifted: sales-per-warehouse growth, net new warehouses, gross margin, SG&A %, capex % (operating
drivers, added to every forecast year of the live operating case) and WACC, terminal growth (added in the DCF).
Live shift = manual shift + the selected stress case's shift (0 = no stress case). In the reference, operating shifts
go through `Inputs.flex` (so `live()` returns case + shift) and valuation shifts through `ValInputs.wacc_shift` and
`growth_shift`. Workbooks 01 and 02 do not carry the shift terms (`Inputs.lab` is false), so they are unchanged.

## Results computed by re-running the model
- Tornado: each driver at -1 and +1 step, price under both DCF methods; ranked by the perpetuity-growth swing.
- Spider: each driver at -2, -1, 0, +1, +2 steps.
- Stress cases: the named combinations of shifts.
- Monte Carlo: shifts drawn as independent standard normals x one step, except sales growth and openings drawn with
  correlation 0.5 (z_b = rho z_a + sqrt(1 - rho^2) z_b); a draw whose WACC is less than one point above terminal
  growth is redrawn. Seeded (`random.Random(seed)`), so the same seed gives the same numbers. Outputs: mean,
  percentiles (Excel PERCENTILE, inclusive), share of trials above the market price, and a 20-bin histogram.

## Checks
Live price = reference at the base case (when no shift is set); live price = reference at the selected stress case
(when no manual shift is set); histogram counts sum to the trials; plus every three-statement and valuation check.
Tests rebuild the workbook at each stress case and with manual shifts and compare the live prices with a full
reference re-run on both calculation engines. `ledgerline.xl.montecarlo` repeats the Monte Carlo inside Excel
through xlwings, trial by trial, as the Excel-side cross-check (M10).
