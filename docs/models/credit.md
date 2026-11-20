# Model spec: credit analysis (workbook 09, 11 US retailers)

Reference: `ref/credit.py`. Inputs: `spec/CREDIT.yaml` (judgement, Altman coefficients cited) and each borrower's latest
fiscal year in `fixtures/<TICKER>`. Columns are borrowers. Units $m.

## Spreads
Debt = current debt + long-term debt + short-term borrowings; leases = operating lease liabilities (current + non-current).
Interest for coverage = gross interest expense, or net non-operating interest where gross is not tagged (DG, KR, LOW tag
only the net figure). Retained earnings and net non-operating interest were added to the data layer as memo items for
this workbook (purely additive fixture change).

## Metrics
EBITDA = EBIT + D&A. Lease-adjusted debt = debt + leases; net = less cash and short-term investments. Leverage =
adjusted debt / EBITDA; coverage = EBITDA / interest; EBIT coverage; FCF = CFO + capex; FCF / debt; CFO / debt.
Altman Z' = 0.717 WC/TA + 0.847 RE/TA + 3.107 EBIT/TA + 0.420 book equity/TL + 0.998 sales/TA; distress below 1.23, safe
above 2.90 (Altman 1983, book-equity form so private and delisted borrowers are scored the same way).

## Scorecard
Leverage band = 1 + number of leverage bounds below the ratio; coverage band = 1 + number of coverage bounds above it.
Band = ROUND(w x leverage band + (1 - w) x coverage band, 0) (half away from zero), plus one notch in the Altman distress
zone, capped at the last band. Rating and illustrative one-year PD by band. The grid is a simplified, judgemental
stand-in for agency methodologies; it is not, and is not calibrated to, any agency's ratings.

## Covenants and capacity
Leverage headroom = 1 - adjusted debt / (max leverage x EBITDA); coverage headroom = 1 - min coverage x interest / EBITDA;
binding headroom = the smaller. Capacity = min(target leverage x EBITDA - adjusted debt, (EBITDA / min coverage - interest) /
marginal rate).

## Stress
EBITDA x (1 - shock); interest + rate shock x floating share x debt (leases excluded); Z' with EBIT reduced by the EBITDA
loss; bands, rating, PD as above; breach = leverage above or coverage below the covenant package.

## Checks
Each borrower's balance sheet balances; bands inside the grid; PDs rise with band; stress never improves a rating.

## Exports
`exports/borrower_spreads.csv` (banking-risk) and `exports/fundamental_signals.csv` (Tickforge); schemas in
`docs/interfaces/`, contract and freshness tests in `tests/test_credit.py`.
