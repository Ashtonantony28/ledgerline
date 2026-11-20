# Scenario lab memo: what the uncertainty says about Costco (workbook 07)

**Status:** first pass, 2026-11-20. Numbers from `07_COST_ScenarioLab.xlsx` (equal to `ref/lab.py`), base operating
case, market price $1,093.83 (the fixture snapshot used by workbook 02).

## The headline
The base DCF gives $383 a share (perpetuity growth, WACC 9.0%, terminal growth 3.0%) or $516 (exit multiple at the
comps median). Across 10,000 simultaneous shifts of the seven drivers, the 95th percentile is $697 (perpetuity growth)
and $780 (exit multiple); fewer than 0.2% of trials reach the market price. The reverse DCF says why: the market
price needs perpetual growth of about 7.5% at this WACC, far above any shift the lab allows.

## Which drivers matter (tornado, one step each way)
| Driver (step) | Price, step down | Price, step up |
|---|---|---|
| SG&A % of revenue (0.5pp) | 446 | 321 |
| Gross margin (0.5pp) | 321 | 446 |
| WACC (1pp) | 455 | 332 |
| Sales per warehouse growth (2pp) | 334 | 443 |
| Capex % of revenue (0.5pp) | 437 | 329 |
| Net new warehouses (10 a year) | 361 | 406 |
| Terminal growth (0.5pp) | 366 | 404 |

Half a point of margin is worth about $60 a share either way. That is the core of the Costco model: on a 12-13% gross
margin and roughly 9% SG&A, a few tenths of a point is a large share of operating profit. Warehouse openings matter
least, because each new warehouse adds revenue at the same thin margin.

## Stress cases
| Case | Perpetuity growth | Exit multiple |
|---|---|---|
| Consumer slowdown (growth -3pp, 10 fewer openings) | 296 | 394 |
| Margin squeeze (gross margin -1pp, SG&A +0.5pp) | 195 | 332 |
| Rate shock (WACC +1.5pp) | 312 | 463 |
| Combined downturn | 128 | 232 |

## How to read this
The lab does not say Costco is overvalued by two thirds. It says a standard five-year DCF with a 3% fade cannot
reproduce a price that capitalises decades of compounding membership income; the market is paying for a growth
runway well beyond the forecast. The defensible output is the range and the ranking: margin discipline dominates,
and the market price sits outside the model's plausible distribution, which is the question an analyst should take
to the investment committee.

Not tuned: no input was changed to bring the distribution towards the market price (CLAUDE.md rule 5).
