# M&A back-test memo: DICK'S Sporting Goods / Foot Locker (workbook 04)

**Status:** first pass, 2026-11-20. Model numbers are from `04_DKS_FL_MnA.xlsx` (equal to `ref/mna.py`), base
case, actual election, unless stated. "Actual" figures are from DICK'S FY2025 10-K (fiscal year ended 31 Jan
2026, accession 0001089063-26-000007), which includes Foot Locker from 8 Sep 2025.

## What is real and what is assumed
- **Real (sourced):** $24.00 cash or 0.1168 DKS shares per Foot Locker share with no proration; share counts,
  DICK'S existing 4.3m-share stake, award settlements, transaction costs, the assumed 6.4% notes, every
  purchase-price-allocation input and the Foot Locker management projections (424B3 proxy statement/prospectus,
  accession 0001140361-25-025528); the $100-125m synergy target (announcement 8-K); the actual election
  (FY2025 10-K Note 2).
- **Assumed (judgement):** DICK'S standalone drivers, synergy phasing, costs to achieve, the minimum-cash rule
  that sizes new debt, tax rates, step-up lives.

## Deal mechanics: the model ties to what happened
| | Model | Actual (10-K Note 2) | Gap |
|---|---|---|---|
| Fair value of consideration | $2,509.7m | $2,512.7m | -0.1% |
| Cash paid to Foot Locker holders | $223.0m | $223.0m | 0.0% |
| New DKS shares issued | 9.54m | "9.6 million" | rounding |
| New acquisition debt | none | none (bridge undrawn, no revolver draws) | - |
| Stake gain recognised | $55.5m (full year, at close) | $42.2m (FY2025 mark-to-market) | timing |

The prospectus's two scenarios also tie: consideration $2,318.1m all cash and $1,998.3m all stock, to the
dollar (tested in `tests/test_mna.py`). Because 89.8% of holders took stock, no new debt was needed; the all-cash
case would have needed about $1.76bn of notes (prospectus: $1.73bn) and taken pro forma leverage from ~0.1x to 0.9x.

**A point the model makes clear:** with a fixed exchange ratio, DICK'S share price rising from $176.74 (June) to
about $224.65 (close) raised the stock consideration by about $460m and moved it all into goodwill, but did not change
EPS accretion at all. Dilution depends on the share count, which was fixed at signing.

## Purchase price allocation: the appraisal moved a lot
| | Model (prospectus inputs on the 1 Feb 2025 balance sheet) | Actual (8 Sep 2025, preliminary) |
|---|---|---|
| Identified intangibles (trade names) | 220 | 710 |
| Property and equipment | ~1,015 (book 910 + 105 step-up) | 698 |
| Deferred tax liabilities | 14 (step-ups only) | 153, plus $286m valuation allowance on DTAs |
| Net identifiable assets | 2,133 | 1,894 |
| Goodwill | 376 | 619 |

The final appraisal valued the Foot Locker banners at $710m (relief from royalty) rather than $210m, wrote
property and equipment down by about $300m instead of stepping it up, and reserved Foot Locker's foreign tax
assets. The prospectus itself had cut trade names to $20m in its all-stock scenario to avoid a bargain purchase;
this model keeps fair values independent of the consideration and books a $135m bargain gain in that scenario
instead, which is what ASC 805 requires if the fair values are right.

## Earnings: the operating case was wrong
| | Model | Actual |
|---|---|---|
| Foot Locker net income | +$175m in FY2025 (management projections, full year) | -$60m from 8 Sep to 31 Jan |
| Acquisition-related charges, FY2025 | ~$157m pre-tax (costs at close + integration) | $390m: inventory write-down $218m, merger and integration $164m, bridge fees $8m |
| Pro forma diluted EPS, FY2025 (GAAP, full year) | $12.82 | $8.30 (10-K pro forma note) |
| FY2026 diluted EPS | $15.01 GAAP, $15.37 adjusted | guidance $13.70-14.70 (incl. ~$150m acquisition costs) |

The model's accretion (+2.8% in FY2025, +12.5% in FY2026, adjusted) rests on Foot Locker earning what its
management projected: adjusted EBITDA of $453m in FY2025 rising to $830m, against $305m of GAAP EBITDA in
FY2024. The deal was priced at 5.0x that projected EBITDA (7.5x FY2024 GAAP EBITDA), so on those numbers it
looks very cheap. The model's own break-even line shows the risk: Foot Locker had to earn at least **$115m after
tax in FY2026** for the deal to be accretive before synergies are counted. Instead it lost money in its first
five months, comparable sales fell 3.3% (international -8.1%), and DICK'S wrote down $218m of inventory and now
expects $500-750m of acquisition-related charges in total. Even the board's tariff downside case
(`Inputs!scenario = 3`) still has Foot Locker earning $160m in FY2025, so none of the filed projections
anticipated this.

The 10-K's own pro forma tells the same story: FY2024 pro forma EPS of $12.34 against DICK'S actual $14.05, a
12% dilution, or about 3% before the $169.5m of deal costs it includes.

## What this back-test says about the model
1. The mechanics are right: consideration, mix, shares, cash and financing tie to the filings within 0.2%.
2. The purchase price allocation can only be as good as the preliminary fair values; the post-close appraisal
   moved intangibles and PP&E by hundreds of millions in opposite directions.
3. Accretion is a function of the target's earnings, and the filed projections were optimistic. The useful outputs
   are the break-even lines (synergies and Foot Locker net income), not the headline accretion.

Not tuned: no input was changed after reading the 10-K (CLAUDE.md rule 5).
