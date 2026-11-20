# Interface: borrower_spreads.csv (Ledgerline -> banking-risk)

Schema version 1.0. Producer: `python -m ledgerline.exports` from `ref/credit.py` (the golden model of workbook 09).
One row per borrower, latest 10-K in the Ledgerline fixtures. Units $m unless stated. Contract tests: `tests/test_credit.py`.

Versioning: adding a column bumps the minor version; renaming, removing or changing the meaning or unit of a column bumps
the major version. Consumers should read columns by name and check `schema_version`.

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
| leverage | float | x | adj_debt / EBITDA |
| coverage | float | x | EBITDA / interest |
| fcf_debt | float | ratio |  |
| altman_z | float | x | Altman Z' (book-equity form) |
| rating | str | band label | simplified scorecard band (AAA..CCC), not an agency rating |
| pd_1y | float | probability | illustrative one-year PD for the band (judgement) |
| covenant_headroom | float | share of EBITDA | EBITDA that can be lost before the 3.5x / 3.0x covenant package breaches |
| debt_capacity | float | $m | additional adj_debt at 3.0x leverage or 4.0x coverage, whichever is lower |
| stressed_rating | str | band label | rating after EBITDA -30% and +200bp on 30% of debt |
| stressed_pd_1y | float | probability |  |
| stressed_breach | int | 0/1 | 1 if the covenant package breaches under stress |
