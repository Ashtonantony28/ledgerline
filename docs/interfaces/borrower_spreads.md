# Interface: borrower spreads (Ledgerline -> banking-risk)

Schema version 1.1. Producer: `python -m ledgerline.exports` from `ref/credit.py` (the golden model of workbook 09).
Units $m unless stated. Contract and freshness tests: `tests/test_credit.py`.

Versioning: adding a column or a companion file bumps the minor version; renaming, removing or changing the meaning or unit
of a column bumps the major version. Read columns by name and check `schema_version`.

Files:
- `borrower_spreads.csv`: one row per borrower, latest 10-K.
- `borrower_spreads_history.csv`: one row per borrower per fiscal year in the fixtures, same columns without the maturity fields
  (maturity tables are kept for the latest 10-K only). Before ASC 842 (fiscal years starting after 15 Dec 2018) operating leases
  were off balance sheet, so `leases` is 0 and lease-adjusted leverage is not comparable across that break.
- `pd_table.csv`: the band grid and illustrative PDs, so the calibration can be tested on its own.

Not provided: secured share of debt (not consistently tagged in XBRL; the borrowers' debt is almost entirely senior unsecured notes).

| column | type | unit | meaning |
|---|---|---|---|
| schema_version | str |  |  |
| ticker | str |  |  |
| cik | int |  |  |
| fy_end | date | ISO 8601 |  |
| revenue | float | $m |  |
| ebitda | float | $m |  |
| interest | float | $m | gross interest expense; net non-operating interest where gross is not tagged (DG, KR, LOW) |
| debt | float | $m |  |
| leases | float | $m |  |
| adj_debt | float | $m | debt + operating lease liabilities |
| net_debt | float | $m | adj_debt - cash - short-term investments |
| fcf | float | $m | cash from operations + capex (cash sign) |
| leverage | float | x | adj_debt / EBITDA (blank if EBITDA <= 0) |
| coverage | float | x | EBITDA / interest (blank if no interest) |
| fcf_debt | float | ratio |  |
| altman_z | float | x | Altman Z' (book-equity form) |
| rating | str | band label | simplified scorecard band (AAA..CCC), not an agency rating |
| pd_1y | float | probability | illustrative one-year PD for the band (pd_table.csv) |
| covenant_headroom | float | share of EBITDA | share of EBITDA that can be lost before the 3.5x leverage / 3.0x coverage package breaches |
| debt_capacity | float | $m | additional adj_debt at 3.0x leverage or 4.0x coverage, whichever is lower |
| stressed_rating | str | band label | rating after EBITDA -30% and +200bp on 30% of debt |
| stressed_pd_1y | float | probability |  |
| stressed_breach | int | 0/1 | 1 if the covenant package breaches under stress |
| sic | str | SEC SIC code | SEC SIC code (data.sec.gov submissions) |
| sic_description | str |  |  |
| debt_due_1y | float | $m | 10-K maturity table: principal due in the next 12 months; blank if not tagged (DKS, FL) |
| debt_due_after_1y | float | $m | debt - debt_due_1y (includes short-term borrowings, which the maturity table omits) |
| wam_years | float | years | weighted-average maturity: years 1-5 at mid-year, the after-year-5 bucket at 10 years (judgement) |

pd_table.csv:

| column | type | unit |
|---|---|---|
| schema_version | str |  |
| band | int | 1 = best |
| rating | str | band label |
| pd_1y | float | probability |
| leverage_upper_bound | float | x, blank for the last band |
| coverage_lower_bound | float | x, blank for the last band |
