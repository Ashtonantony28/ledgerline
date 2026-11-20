# Model spec: month-end close and consolidation (workbook 05, synthetic group)

Reference: `ref/group.py`. Inputs: `fixtures/group/` written by the seeded generator `data/group.py`
(seed 2026; regenerating is a reviewed change, and `tests/test_group.py` proves it is deterministic). The group
is synthetic on purpose: public filings do not disclose ledgers, so the close is tested on books whose every
balance is known. Units $m; S2 keeps GBP books until translation.

## Group
| Entity | Country | Currency | Ownership | Notes |
|---|---|---|---|---|
| P | US | USD | parent | sells goods to S1, charges S2 a management fee, lends to S3, holds a 30% associate |
| S1 | US | USD | 100% | buys from P at a markup; some of that stock is still on hand at year-end |
| S2 | UK | GBP | 100% | pays the fee; translated at the current rate |
| S3 | US | USD | 80% | acquired earlier for consideration plus NCI at fair value (full goodwill); pays a dividend |

Sign convention in the trial balances: debit positive, credit negative. Statements show the usual signs (ADR 0002).

## Close journals (on the unadjusted trial balance)
- J1 depreciation = (opening cost + half of this year's additions) / life, per entity.
- J2 prepaid amortisation = amount x months elapsed / term.
- J3 accruals for costs not yet billed.
- J4 revenue cut-off at P: reverse revenue and cost of goods shipped after year-end.
- J6 intercompany cash in transit: P's receivable from S1 is reduced and cash increased.
- J7 equity-method share of the associate's net income (30%).
- J5 income tax = rate x max(0, adjusted pre-tax income), posted last. Equity-method income, dividends received,
  the tax line itself and dividends declared are outside the tax base (judgement; the model is not a tax provision).
Adjusted TB = unadjusted + SUMIFS of the journals by entity and account; each journal and each TB sums to zero.

## Translation (ASC 830, current-rate method, S2)
Assets and liabilities at the closing rate; revenue, expenses and dividends at the average rate; share capital at
the historical rate; opening retained earnings at the carried USD amount. The CTA is the balancing figure, and is
cross-checked by a roll-forward: CTA close = CTA open + opening net assets x (close - open) + net income x (close - avg).

## Eliminations (by statement line, USD)
E1-E2 investment in S1 and S2 against their share capital. E3 acquisition of S3: share capital and retained
earnings at acquisition out, goodwill = consideration + NCI fair value - net assets at acquisition, NCI in.
E4 NCI share of S3's post-acquisition opening retained earnings. E5 NCI share of S3's net income. E6 S3 dividend:
parent's share against dividend income, NCI share against NCI. E7 intercompany trade balance (after J6).
E8 intercompany loan. E9 intercompany sales against cost of sales. E10 unrealised profit in S1's closing stock =
intercompany stock x margin. E11 management fee. E12 intercompany interest. Every elimination sums to zero.

## Statements
Consolidated line = sum of entity columns (S2 translated) + eliminations. Net income attributable to the parent =
group net income - NCI income. Retained earnings close = parent's opening + parent's net income - parent's dividends
(the dividend line is shown negative). NCI check: 20% x S3 net assets + NCI share of goodwill = NCI on the balance sheet.

## Cash flow (indirect)
For each entity, the cash effect of a balance-sheet account is -(closing - opening) of its TB balance, grouped by
the account's cash-flow line; net income comes from the adjusted TB. S2 is translated at the average rate.
Eliminations: dividends paid to the parent and the unrealised profit come out of operating cash flow; the
intercompany loan movement comes out of investing and financing. The effect of exchange rates on cash =
S2 closing cash x closing rate - opening cash x opening rate - movement x average rate.

## Reconciliations
Bank: statement - outstanding cheques + deposits in transit = adjusted cash, per entity. Intercompany: each pair
(trade, loan, sales, fee, interest, dividend) nets to zero after the close journals; the trade pair before J6 shows
the cash in transit as the reconciling item.

## Checks
Each journal and each adjusted TB sums to zero; translated TB sums to zero; CTA plug = CTA roll-forward; each
elimination sums to zero; consolidation worksheet sums to zero; assets = liabilities + equity; NCI check; cash flow
ties to the balance-sheet cash; per-entity cash flow ties to the change in cash; bank and intercompany recs zero.
