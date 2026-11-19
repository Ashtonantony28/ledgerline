# Model spec: DCF, trading comps and football field (workbook 02)

Workbook 02 = the three-statement sheets (docs/models/three-statement.md) plus the sheets below.
Reference: `ref/dcf.py`. Inputs: `fixtures/market.json` (risk-free, ERP, beta, 52-week range),
`fixtures/prices.csv`, comps fixtures, `spec/<TICKER>.yaml` `valuation:` block.

## Cost of capital
Adjusted beta = w x raw + (1 - w) (Blume, w = 0.67). Ke = rf + beta_adj x ERP.
Kd = (rf + credit spread) x (1 - marginal tax). Weights: market cap (price x cover-page shares) and book debt
(last balance sheet, including revolver). WACC = Ke x E/(D+E) + Kd x D/(D+E).

## Unlevered free cash flow (forecast years)
UFCF = EBIT x (1 - tax rate) + D&A - capex + working-capital cash impact. SBC is not added back (it is a real
cost to shareholders; the share count also reflects it).
Discount period = forecast year # - mid-year adjustment (0.5). Discount factor = 1 / (1 + WACC)^period.

## Terminal value and equity value
Gordon: TV = UFCF_N x (1 + g) / (WACC - g), discounted with the final year's factor (mid-year consistent).
Exit: TV = EBITDA_N x comps median EV/EBITDA, discounted at the end of year N.
Net debt = debt + revolver - cash - short-term investments + NCI (last balance sheet; lease liabilities excluded,
consistent with UFCF after lease cost). Equity value = EV - net debt. Implied price = equity / cover-page shares,
rolled forward from fiscal year end to the price date at (1 + Ke)^years.
Implied exit multiple = Gordon TV / EBITDA_N. Implied growth from exit = (TV x WACC - UFCF_N) / (TV + UFCF_N).
Reverse DCF: market EV = price / roll x shares + net debt; TV needed = (market EV - sum PV) / final factor;
implied g from the same closed form.

## Comps
EV = price x shares + debt - (cash + ST investments) + NCI, latest fiscal year, not calendarised. EBITDA = operating
income + D&A. Statistics: MEDIAN, AVERAGE, MAX, MIN, QUARTILE (inclusive, linear interpolation).

## Sensitivity and football field
Grids: WACC across (base +/- 1 and 2 steps), terminal growth or exit multiple down. Football field: DCF ranges are
the min/max of the inner 3 x 3 of each grid; comps ranges apply the 25th/75th percentile multiple to last-year
EBITDA (EV/EBITDA, then less net debt, per share) or diluted EPS (P/E); plus the 52-week range.

## Checks
WACC > terminal growth; every football-field low <= high.
