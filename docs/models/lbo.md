# Model spec: LBO (workbook 03, Skechers / 3G Capital)

Reference: `ref/lbo.py`. Inputs: `spec/SKX_LBO.yaml` (transaction terms sourced from the DEFM14C
information statement; judgement items labelled), `fixtures/SKX`. Units $m. Deal modelled as if it
closed at FY2024 year end; the last history column of the Debt sheet shows pro forma balances at close.

## Sources and uses
Uses = cash consideration + rollover equity + debt repaid + financing fees/OID + revolver fees + transaction costs.
Sources = USD term loan + EUR term loan (total less USD) + senior secured notes + PIK toggle notes + sponsor
equity + rollover + balance-sheet cash (plug). Cash at close = FY2024 cash - cash used.
E0 = sponsor + rollover. Net claims at close = new debt + remaining existing debt (pre-deal debt - repaid) -
cash at close + NCI (book + redeemable). Entry EV = E0 + net claims (includes fees); entry multiple = entry EV /
FY2024 EBITDA. Headline EV = offer equity + pre-deal debt - pre-deal cash and ST investments + NCI.

## Operating model (forecast)
Revenue grows at g; EBITDA = revenue x margin; D&A and capex % revenue; trade working capital % revenue,
cash impact = NWC(t-1) - NWC(t). Taxes = max(0, EBIT - total interest) x cash tax rate. NI = EBIT - interest - tax.
NCI distributions = NCI% x max(0, NI). Levered FCF = EBITDA - capex + NWC impact - taxes - cash interest - NCI.

## Debt (interest on opening balances, no circularity)
Term loans: amortise 1% of original principal a year (capped at balance); USD at SOFR + 325bp, EUR at Euribor +
350bp (EUR debt held at the closing USD equivalent; no FX revaluation). Senior secured notes 5.25%, bullet.
PIK toggle notes: 10.75% accrued to principal when the toggle is 1, else 10.00% cash. Revolver: SOFR + margin
on drawn, commitment fee on undrawn. Remaining existing debt held flat at its rate.
Cash before revolver = opening cash + LFCF - amortisation. Revolver draw = min(max(min cash - cash, -opening
revolver), capacity - opening revolver). Excess = max(0, cash + draw - min cash). Sweep = min(excess x sweep%,
term loans after amortisation), split pro rata between USD and EUR term loans. Closing cash = cash + draw - sweep.
Credit stats: first-lien net leverage = (term loans + SSN + revolver - cash) / EBITDA; total net leverage; EBITDA /
cash interest; covenant headroom vs the springing first-lien level (a breach is flagged, not a model error).

## Returns
Exit at end of year X (input). Exit EV = EBITDA_X x exit multiple (= entry multiple). NCI claim = NCI at close x
EBITDA_X / EBITDA_0. Exit equity = EV - net debt - NCI claim; to investors = x (1 - MIP%). MOIC = investor equity /
E0; IRR via IRR() on the cash-flow row and in closed form. Bridge: EBITDA growth (delta EBITDA x entry multiple) +
multiple expansion + fall in net claims + MIP = value created (checked).

## Sensitivities
IRR by offer price (E0 changes by delta price x shares and awards, debt held fixed) x exit multiple; IRR by exit
year (INDEX into the forecast) x exit multiple. Both closed form, single entry and exit cash flow.
