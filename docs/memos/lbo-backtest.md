# LBO back-test memo: Skechers / 3G Capital (workbook 03)

**Status:** first pass, 2026-11-19. Numbers below are from the base case of `03_SKX_LBO.xlsx` (equal to `ref/lbo.py`).

## What is real and what is assumed
- **Real (sourced):** offer price ($63.00), share and award counts, cash consideration ($9,500m), rollover ($742m),
  debt repaid ($130m), fees and costs, and the whole financing package: $1.6bn USD + EUR 1.25bn term loans
  (SOFR + 325 / Euribor + 350), EUR 1.0bn 5.25% senior secured notes, $2.2bn 10.00%/10.75% PIK toggle notes,
  $1.6bn revolver, $3.5bn sponsor equity. Source: DEFM14C information statement, accession 0001104659-25-074187.
- **Assumed (judgement):** operating paths, rate paths, sweep, minimum cash, covenant level, tax rate, MIP, exit
  at the entry multiple after five years. The credit agreement and the sponsor's model are not public.

## Entry
- Headline EV / FY2024 EBITDA: **9.0x** (offer equity + net debt + NCI). Including fees and the cash used: 9.3x.
- Total debt at close / FY2024 EBITDA: **6.0x**, of which the holdco PIK notes are 2.0x. First-lien net leverage
  starts at 2.8x, so the structure leans on junior, expensive PIK paper: 3G paid with leverage it could only get
  at 10%+.

## Returns (five-year hold, exit at 9.35x)
| Case | IRR | MOIC | Year-5 total net leverage | Lowest EBITDA / cash interest |
|---|---|---|---|---|
| Base | 13.3% | 1.86x | 3.4x | 2.6x |
| Upside | 21.6% | 2.66x | 2.5x | 3.0x |
| Downside | -6.3% | 0.72x | 5.6x | 1.8x |

The base-case value bridge is almost all EBITDA growth (+$3.7bn); deleveraging adds only +$0.3bn because PIK
accrual offsets term-loan paydown in years 1-2. At a 13% base IRR, 3G's case needs margin expansion or a higher
exit multiple to reach a typical 20% target; at a $57 offer price the base IRR would be about 19% (Sensitivity sheet).

## Back-test against reported results (Skechers 10-Q, six months to 30 June 2025, accession 0000950170-25-105871)
| | H1 2025 actual | Model FY2025 (base) |
|---|---|---|
| Revenue growth | +10.0% (4,851.6 vs 4,409.2) | +6.0% |
| EBITDA margin (EBIT + D&A) | 11.4% (H1 2024: 13.7%) | 11.5% |

The model's year-1 margin matched the first half closely: the tariff squeeze was real. Revenue growth was
under-called: the business kept growing at about 10% through the first half despite withdrawn guidance.
Skechers stopped filing after the 12 September 2025 close, so later periods cannot be checked from EDGAR.
Next step (M10): re-run the base case with H1 run-rate growth and report the IRR change rather than re-tuning.
