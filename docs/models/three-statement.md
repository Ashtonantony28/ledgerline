# Model spec: three-statement operating model (workbook 01)

Both the workbook (`models/three_statement.py`) and the reference (`ref/three_statement.py`) implement this
document. Units $m. `t` is a forecast year, `t-1` the prior year (year 0 = last actual). Drivers come from the
live scenario (Inputs!scenario chooses Base / Upside / Downside on the Drivers sheet).

## Opening balances (year 0, from Hist)
Debt = current + long-term + short-term debt. Other current liabilities (OCL) = accrued + employee + deferred
revenue + other current liabilities. Operating lease liabilities = current + non-current. Revolver = 0.
Revenue per store(0) = revenue(0) / average(stores(0), stores(-1)). Share price(0) = market snapshot.

## Revenue
stores(t) = stores(t-1) + openings(t); avg stores = average of the two; revenue per store(t) =
revenue per store(t-1) x (1 + growth(t)); revenue = avg stores x revenue per store.

## Operating lines
COGS = revenue x (1 - gross margin); SG&A = revenue x SG&A%; other opex = revenue x other%;
EBIT = revenue - COGS - SG&A - other. D&A = D&A% x PP&E(t-1) (embedded in COGS/SG&A, shown as memo);
EBITDA = EBIT + D&A. Capex = revenue x capex%; PP&E(t) = PP&E(t-1) + capex - D&A.

## Working capital
Receivables = revenue x days / days-in-year; inventory and payables = COGS x days / days-in-year;
other current assets = revenue x %; OCL = revenue x %. NWC = AR + inventory + OCA - AP - OCL;
cash impact = NWC(t-1) - NWC(t). SBC = revenue x SBC%.

## Debt, distributions, revolver
Repayment = min(scheduled maturity, opening debt); issuance = maturity x refinance%; debt(t) = debt(t-1) -
repayment + issuance. Interest on debt = rate x (circ ? average : opening) debt; revolver likewise at the
revolver rate; interest income = cash rate x (circ ? average : opening) cash.
Pre-tax = EBIT - interest expense + interest income; tax = pre-tax x tax rate; NCI and other below tax = 0.
Regular dividends = -max(NI, 0) x payout; buybacks = -max(NI, 0) x buyback%.
CFO = NI + D&A + SBC + NWC cash impact; CFI = -capex.
Cash available = cash(t-1) + CFO + CFI + dividends + buybacks + issuance - repayment.
Special dividend = -max(0, cash available - cash ceiling); cash before revolver = available + special.
Revolver draw = min(max(min cash - cash before revolver, -revolver(t-1)), capacity - revolver(t-1)).
Cash(t) = cash before revolver + draw. CFF = dividends + special + buybacks + issuance - repayment + draw.

## Equity and shares
Equity(t) = equity(t-1) + NI + dividends + special + buybacks + SBC.
Price(t) = price(t-1) x (1 + growth); shares(t) = shares(t-1) + (SBC + buybacks) / price(t); EPS = NI / shares.

## Held flat
Short-term investments, operating-lease ROU assets and liabilities, goodwill, intangibles, other non-current
assets and liabilities, NCI equity.

## Checks
Assets = liabilities + equity every year; forecast change in BS cash = CF net change; historical CF sums to the
reported change in cash; historical NI, EBIT, total assets and total liabilities equal the filed values;
revolver within [0, capacity]; debt non-negative.
