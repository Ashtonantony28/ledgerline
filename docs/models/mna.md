# Model spec: M&A accretion / dilution (workbook 04, DICK'S Sporting Goods / Foot Locker)

Reference: `ref/mna.py`. Inputs: `spec/DKS_FL_MA.yaml` (merger terms and purchase-price-allocation inputs
sourced from the 424B3 proxy statement/prospectus; Foot Locker management projections from the same
document; judgement labelled), `fixtures/DKS` (cut off at FY2024, the last pre-deal 10-K), `fixtures/FL`.
Units $m, shares in millions. Fiscal years use the companies' naming (FY2024 ends 1 Feb 2025). Like the
filed pro formas, the deal is modelled as if it closed at the start of FY2025 on the 1 Feb 2025 balance sheets.

## Switches
Operating case (base / upside / downside) selects DICK'S drivers, Foot Locker projections and the synergy
run-rate. Consideration mix: 1 all cash and 2 all stock (the prospectus's Scenarios A and B, DKS at $176.74),
3 the actual election (89.8% stock, DKS at the implied closing price $224.65).

## Consideration
N = Foot Locker shares - shares already held by DICK'S. New DKS shares = N x stock% x 0.1168. Cash to holders
= N x (1 - stock%) x $24.00. Stock value = new shares x DKS price. Blended value per share = stock% x 0.1168 x
DKS price + (1 - stock%) x $24.00; existing stake at fair value = held shares x blended value (gain = fair value -
carrying value). Consideration = cash + awards settled in cash + stock + stake + replaced awards.

## Financing
Cash uses = cash to holders + awards + DICK'S transaction costs + severance + retention + Foot Locker's own
costs. Cash available = DKS cash + FL cash - minimum cash. New notes = max(0, (uses - available) / (1 - fee%));
issuance cost = notes x fee%; balance-sheet cash used = uses + issuance cost - notes.

## Purchase price allocation
Tangible book = FL equity - existing goodwill - existing intangibles. Net identifiable assets = tangible book +
intangibles at fair value + PP&E step-up + favourable leases + notes fair-value discount - deferred tax - FL
transaction costs assumed. Deferred tax = PF tax rate x (PP&E step-up + intangibles FV - book intangibles +
leases + notes discount). Goodwill = max(0, consideration - net assets); a negative excess is a bargain
purchase gain (ASC 805-30-25-2), recognised in year 1.

## Standalone forecasts
DICK'S: revenue grows at g; EBITDA = revenue x margin; D&A % revenue; interest expense held at FY2024;
interest income = FY2024 cash x yield; tax at the DICK'S rate; diluted shares held at FY2024 (no buybacks in
either case, so accretion isolates the deal). Foot Locker: revenue and adjusted EBITDA from the projections;
D&A % revenue; interest held at FY2024; tax at the Foot Locker rate.

## Pro forma
Pre-tax adjustments: + synergies (run-rate x phase) - PP&E step-up depreciation - finite intangible amortisation
- favourable lease amortisation - accretion of the notes discount + FL historical amortisation eliminated -
interest on new notes - issuance cost amortisation - interest forgone on cash used. Each step-up is straight
line, stopping once fully amortised: charge_k = max(0, min(S/L, S - S/L x (k - 1))).
Adjusted NI = DKS NI + FL NI + adjustments x (1 - PF tax). GAAP NI = adjusted - (one-time items + integration
costs) x (1 - PF tax); one-time items (year 1) = transaction costs + severance + retention - stake gain - bargain
gain. Shares = DKS shares + new shares. Accretion = PF EPS / standalone EPS - 1, adjusted and GAAP.
Breakeven synergies = synergies - (adjusted NI - standalone EPS x PF shares) / (1 - PF tax). Foot Locker
breakeven NI = FL NI - (adjusted NI - standalone EPS x PF shares).
Credit: PF debt = DKS debt + FL debt - notes discount + new notes; net debt held at the closing level;
leverage = net debt / (DKS EBITDA + FL EBITDA + synergies). Contribution (year 1): DICK'S share of revenue,
EBITDA and NI; ownership = DKS shares / PF shares and new shares / PF shares.

## Sensitivities (closed form)
Test year = input (FY2026, the first full year after the September 2025 close). Grid 1: offer price X (rows)
x stock share s (columns). The exchange ratio scales with the price (0.1168 x X / $24); cash uses, notes,
issuance cost and cash used are recomputed; financing cost = notes x rate + issuance cost / term + cash used x
yield; accretion = (adjusted NI before financing - financing x (1 - t)) / (DKS shares + new shares) / standalone
EPS - 1. Grid 2: forecast year (rows) x synergy realisation f (columns): (adjusted NI + (f - 1) x synergies x
(1 - t)) / PF shares / standalone EPS - 1.

## Checks
Sources = uses; goodwill - bargain gain = consideration - net assets; cash after close >= minimum; ownership
sums to 100%; adjusted NI = combined pre-tax - combined tax (computed independently); EPS at breakeven
synergies = standalone EPS; synergy grid at 100% = the accretion row.
