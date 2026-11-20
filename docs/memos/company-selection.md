# M0 memo: company and deal selection

**Decision D4** (approved plan): M0 proposes companies using a rubric; final picks can be changed by Ashton.

## Rubric
1. Clean US-GAAP XBRL tagging for the main lines (few extension tags), so the tie-out passes with small plugs.
2. A business simple enough to explain in an interview, with a real operating driver to build revenue from.
3. Enough disclosure for schedules (debt maturities, leases, SBC, share count).
4. For transaction workbooks: a real public deal to back-test against.
5. Not a bank or insurer (those belong to the banking-risk project).

## Operating company A: Costco Wholesale (COST) - selected
All hard tie-outs pass for FY2017-FY2026 with one soft warning; warehouse count (`NumberOfStores`) is tagged,
giving a warehouses x sales-per-warehouse revenue build; the debt maturity ladder is tagged; capital-light, net
cash, and a history of special dividends, which makes the cash and distribution logic interesting.

## Comparable set (trading comps, workbook 02)
Walmart (WMT), Target (TGT), BJ's Wholesale (BJ), Dollar General (DG), Kroger (KR), Home Depot (HD), Lowe's (LOW).
All tie out for FY2022-FY2026. Kroger reports OG&A with an extension tag, so its SG&A lands in the other-opex
plug; it is used for EV/EBITDA and P/E only. BJ's is the closest pure-play warehouse club.

## LBO back-test (workbook 03): Skechers (SKX) / 3G Capital, 2025 - proposed
Announced May 2025, $63.00 per share cash, about $9.4bn; financed with committed debt; closed September 2025.
Public 10-K history to FY2024, merger proxy with financing terms. A real take-private by a PE sponsor with a
consumer business similar enough to model with the same operating template.

## M&A back-test (workbook 04): DICK'S Sporting Goods (DKS) / Foot Locker (FL), 2025 - chosen at M5
Signed 15 May 2025, closed 8 Sep 2025: $24.00 cash or 0.1168 DKS shares per Foot Locker share, no proration.
Meets every criterion: public-to-public, S-4 / 424B3 with full pro forma notes (PPA inputs, financing
assumption, two consideration scenarios) and Foot Locker management projections, a $100-125m synergy target,
and DICK'S FY2025 10-K (filed March 2026) with the actual election, consideration and preliminary PPA. Same
retail template as the other models. Back-test: docs/memos/mna-backtest.md.
