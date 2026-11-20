# Model spec: FP&A budget, rolling forecast and variance (workbook 06, synthetic group)

Reference: `ref/fpa.py`. Inputs: `spec/FPA.yaml` (assumptions, judgement with rationale; FY2025 anchors from
workbook 05) and `fixtures/fpa/` (seeded GL export from `data/fpa.py`, deterministic). Units $m, volumes in millions
of units, headcount in people. Monthly timeline: 9 actual months (Jan-Sep 2026) then a 12-month rolling forecast
(Oct 2026-Sep 2027). The budget year is the first 12 months; the budget is zero outside it (in-budget flag).

## Calendar rows
seq = 1, 2, ...; month of year = MOD(previous, 12) + 1; in-budget = 1 if seq <= 12; seasonality = weight for the
month of year (weights sum to 1).

## Budget (FY2026)
FY2025 volume_p = share_p x FY2025 revenue / FY2025 price_p. Budget volume = FY2025 volume x (1 + growth) x
seasonality x in-budget; price = FY2025 price x (1 + increase); unit cost = FY2025 unit cost x (1 + inflation).
Heads = opening heads + cumulative hires; people cost = heads x cost per head x (1 + pay rise) / 12. Non-people:
sales and marketing = % of budget revenue; operations and G&A = annual amount / 12. EBITDA = revenue - COGS - opex.

## Live drivers
Actual months: volume, heads and non-people cost from the GL; price = revenue / volume, unit cost = COGS / volume,
cost per head = people cost / heads (realised). Forecast months (selected case):
- volume = run-rate x seasonality x growth index; run-rate = sum of the last 3 actual volumes / sum of their
  seasonality weights (deseasonalised, annual); growth index compounds the case's monthly growth from 1;
- price = previous x (1 + case price change); unit cost = previous x (1 + monthly cost inflation);
- heads = previous + case net hires; cost per head = previous x (1 + monthly wage inflation);
- sales and marketing non-people = (last-3-month spend / last-3-month revenue) x revenue; other non-people =
  last-3-month average; capex = monthly assumption.

## Outlook P&L and cash
Revenue and COGS by product = volume x price, volume x unit cost. Depreciation = FY2025 depreciation / 12 +
cumulative capex / life of new capex. Tax = rate x max(0, EBIT). Net working capital = (FY2025 NWC / FY2025
revenue) x monthly revenue x 12; the first month's previous NWC is FY2025 closing NWC. FCF = EBITDA - tax - increase
in NWC - capex; cash = previous + FCF from FY2025 closing cash. Lowest forecast cash over the forecast months, its
month, and headroom over the minimum-cash policy.

## Variance bridges (YTD = actual months; FY = budget year, actual + forecast)
With AV, AR, AC the actual volume, revenue, COGS by product over the scope, BV, BR, BC the budget equivalents, BP =
BR/BV, BC/BV the budget unit cost, BGP = BR - BC in total, and totals AVt, BVt, BRt:
- price = sum(AR - AV x BP); volume (revenue) = (AVt - BVt) x BRt / BVt; mix (revenue) = sum(AV x BP) - AVt x BRt / BVt.
  Price + volume + mix = actual - budget revenue.
- unit cost = -sum(AC - AV x BC/BV); volume (margin) = (AVt - BVt) x BGP / BVt; mix (margin) = sum(AV x (BR - BC)/BV) -
  AVt x BGP / BVt. Price + cost + volume + mix = actual - budget gross profit.
- by department: headcount = (actual - budget head-months) x budget cost per head-month; pay rate = actual people cost
  - actual head-months x budget cost per head-month; non-people = actual - budget. Sum = opex variance.
- EBITDA: budget + price + cost + volume + mix - headcount - pay rate - non-people = actual/outlook EBITDA.

## Forecast accuracy
The forecast made at the June close (fixtures/fpa/prior_forecast.csv) against actual revenue for Jul-Sep: error =
forecast - actual, APE = |error| / actual, MAPE = mean APE, bias = total error / total actual; the change in the
outlook for Oct-Dec since June.

## Checks
Seasonality and product shares sum to 100%; product revenue and department opex tie to the GL control totals every
actual month; budget months phase to the annual plan; each bridge sums (YTD and FY: revenue, opex, EBITDA); closing
cash = opening cash + cumulative FCF.
