"""Seeded synthetic group for workbook 05 (close and consolidation). No real GL data is public (plan §3).

    python -m ledgerline.data.group            # writes fixtures/group/ (a reviewed change)

The generator simulates a year of double-entry postings for four entities and writes what a controller
would receive at year end: opening balance sheets, unadjusted closing trial balances (local currency),
and the close inputs (FX rates, schedules, sub-ledger figures, bank statements). Everything else (close
journals, translation, eliminations, statements) is computed by the workbook and, independently, by
ref/group.py. Same seed, same files: tests regenerate and compare.

Group (synthetic, names invented):
  P   Parent, US, USD       owns S1 100%, S2 100%, S3 80%, and 30% of associate A (equity method)
  S1  US distribution, USD  buys goods from P (intercompany sales with unrealised profit at year end)
  S2  UK retail, GBP        pays P a management fee; translated at the current-rate method (CTA)
  S3  US services, USD      80% owned (NCI 20%, full goodwill); borrows from P; pays dividends
TB sign: debit positive, credit negative; every trial balance sums to zero.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "fixtures" / "group"
SEED = 2026
ENTITIES = ["P", "S1", "S2", "S3"]
SCALE = {"P": 1.0, "S1": 0.45, "S2": 0.20, "S3": 0.45}

# code, name, type (A/L/E/R/X), FS line, cash-flow line (balance-sheet accounts); taxable flag and FX basis
# are derived below (fx basis: close for assets/liabilities, avg for P&L and dividends, hist for share capital,
# "re" for opening retained earnings carried in USD, "cta" for the translation reserve)
ACCOUNTS = [
    (1000, "Cash", "A", "cash", "cash"),
    (1100, "Trade receivables", "A", "receivables", "wc_receivables"),
    (1150, "Intercompany receivables", "A", "ic_receivables", "wc_ic"),
    (1200, "Inventory", "A", "inventory", "wc_inventory"),
    (1300, "Prepaid expenses", "A", "prepaids", "wc_other"),
    (1500, "PP&E at cost", "A", "ppe", "capex"),
    (1510, "Accumulated depreciation", "A", "ppe", "da"),
    (1600, "Investment in subsidiaries", "A", "inv_subs", "inv_subs"),
    (1650, "Investment in associate", "A", "inv_assoc", "assoc"),
    (1700, "Intercompany loan receivable", "A", "ic_loan_rec", "ic_loan_rec"),
    (1800, "Goodwill", "A", "goodwill", "none"),
    (2000, "Trade payables", "L", "payables", "wc_payables"),
    (2050, "Intercompany payables", "L", "ic_payables", "wc_ic"),
    (2100, "Accrued liabilities", "L", "accrued", "wc_other"),
    (2200, "Income tax payable", "L", "tax_payable", "wc_other"),
    (2500, "Long-term debt", "L", "debt", "debt"),
    (2700, "Intercompany loan payable", "L", "ic_loan_pay", "ic_loan_pay"),
    (3000, "Share capital", "E", "share_capital", "equity"),
    (3100, "Retained earnings (opening)", "E", "re_open", "none"),
    (3200, "Dividends declared", "E", "dividends", "dividends"),
    (3300, "Cumulative translation adjustment", "E", "cta", "none"),
    (3400, "Non-controlling interests", "E", "nci", "none"),
    (4000, "Revenue", "R", "revenue", ""),
    (4100, "Intercompany revenue", "R", "ic_revenue", ""),
    (4200, "Management fee income", "R", "fee_income", ""),
    (4300, "Intercompany interest income", "R", "ic_int_income", ""),
    (4400, "Share of associate income", "R", "assoc_income", ""),
    (4500, "Dividend income", "R", "div_income", ""),
    (5000, "Cost of sales", "X", "cogs", ""),
    (6000, "Operating expenses", "X", "opex", ""),
    (6100, "Management fees", "X", "fee_expense", ""),
    (6200, "Depreciation", "X", "depreciation", ""),
    (7000, "Interest expense", "X", "interest", ""),
    (7100, "Intercompany interest expense", "X", "ic_int_expense", ""),
    (8000, "Income tax expense", "X", "tax", ""),
    (9000, "Net income attributable to NCI", "X", "nci_income", ""),
]
CODES = [a[0] for a in ACCOUNTS]
NON_TAXABLE = (4400, 4500, 8000, 9000)


def taxable(code: int, typ: str) -> int:
    return int(typ in ("R", "X") and code not in NON_TAXABLE)


def fx_basis(code: int, typ: str) -> str:
    return {3000: "hist", 3100: "re", 3300: "cta"}.get(code, "close" if typ in ("A", "L") else "avg")


def r3(x: float) -> float:
    return round(x, 3)


class Ledger:
    def __init__(self):
        self.bal = {e: defaultdict(float) for e in ENTITIES}

    def post(self, e: str, dr: int, cr: int, amt: float) -> None:
        amt = r3(amt)
        self.bal[e][dr] += amt
        self.bal[e][cr] -= amt


def generate(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    u = lambda a, b: r3(rng.uniform(a, b))
    fx = {"open": 1.2650, "avg": 1.2875, "close": 1.3120, "hist": 1.4800}  # USD per GBP
    rates = {"interest": 0.055, "ic_loan": 0.050}
    own = {"S3": 0.80, "assoc": 0.30}

    # ---------------------------------------------------------------- opening balance sheets
    sc = {"P": 300.0, "S1": 60.0, "S2": 40.0, "S3": 50.0}
    acq = {"consideration": 72.0, "nci_fv": 18.0, "re_acq": 12.0}      # S3 acquired in an earlier year
    opening = {}
    led = Ledger()
    for e in ENTITIES:
        b = led.bal[e]
        scale = SCALE[e]
        b[1000] = u(40, 60) * scale * (2.5 if e == "S1" else 1.0)
        b[1100] = u(90, 110) * scale
        b[1200] = u(140, 170) * scale if e != "S3" else u(2, 4)
        b[1300] = u(6, 9) * scale
        b[1500] = u(380, 420) * scale
        b[1510] = -u(150, 170) * scale
        b[2000] = -u(70, 90) * scale
        b[2100] = -u(20, 30) * scale
        b[2200] = -u(8, 12) * scale
        b[2500] = -(u(180, 220) * scale if e in ("P", "S2") else 0.0)
        b[3000] = -sc[e]
    P = led.bal["P"]
    P[1600] = r3(sc["S1"] + sc["S2"] * fx["hist"] + acq["consideration"])
    P[1650] = 45.0
    P[1700] = 50.0
    led.bal["S3"][2700] = -50.0
    P[1150] = 20.0
    led.bal["S1"][2050] = -20.0
    for e in ENTITIES:
        b = led.bal[e]
        for k in list(b):
            b[k] = r3(b[k])
        b[3100] = r3(-sum(v for k, v in b.items() if k != 3100))       # opening retained earnings is the plug
        assert b[3100] < 0, f"{e} opening RE should be a credit"
        opening[e] = {k: v for k, v in b.items() if abs(v) > 0}
    assert -led.bal["S3"][3100] > acq["re_acq"]

    # ---------------------------------------------------------------- the year's postings (local currency)
    ic_sales = u(110, 130)
    ic_margin = 0.25
    s1_ic_inventory = r3(ic_sales * u(0.18, 0.24))                        # IC goods still in S1's stock at year end
    in_transit = u(6, 9)                                                  # S1 paid P on the last day; P books it in January
    fee_gbp = r3(round(u(5, 7) / 0.08) * 0.08)   # multiple of 0.08 so fee x 1.2875 is a whole $1k
    loan_advance = 25.0
    div_s3 = 20.0
    assoc_ni, assoc_div = u(28, 34), 6.0
    cutoff = {"revenue": u(3.5, 5.0)}
    cutoff["cost"] = r3(cutoff["revenue"] * 0.62)
    s1_ic_cogs = r3(ic_sales - s1_ic_inventory)
    capex, lives, tax_rates, ext_rev = {}, {"P": 10.0, "S1": 8.0, "S2": 10.0, "S3": 5.0}, \
        {"P": 0.25, "S1": 0.25, "S2": 0.25, "S3": 0.25}, {}
    for e in ENTITIES:
        b = led.bal[e]
        scale = SCALE[e]
        rev = ext_rev[e] = u(880, 940) * scale
        gm = {"P": 0.38, "S1": 0.32, "S2": 0.45, "S3": 0.45}[e]
        cogs = r3(rev * (1 - gm)) - (s1_ic_cogs if e == "S1" else 0.0)   # S1's cost of sales includes IC goods
        led.post(e, 1100, 4000, rev)                                      # credit sales
        close_ar = r3(rev * u(0.09, 0.12))
        led.post(e, 1000, 1100, b[1100] - close_ar)                       # collections
        led.post(e, 1200, 2000, cogs + u(-2, 4) * scale)                  # purchases
        led.post(e, 5000, 1200, cogs)                                     # cost of sales
        led.post(e, 2000, 1000, -b[2000] - r3(cogs * u(0.08, 0.10)))      # supplier payments
        led.post(e, 6000, 1000, rev * (u(0.10, 0.13) if e == "S1" else u(0.18, 0.22)))  # cash operating expenses
        led.post(e, 6000, 1300, b[1300])                                  # opening prepaids expensed
        led.post(e, 2100, 1000, -b[2100])                                 # opening accruals settled
        capex[e] = u(30, 45) * scale
        led.post(e, 1500, 1000, capex[e])
        if b[2500]:
            led.post(e, 7000, 1000, -b[2500] * rates["interest"])
            led.post(e, 2500, 1000, u(15, 25) * scale)                    # debt repayment
        led.post(e, 2200, 1000, -b[2200])                                 # last year's tax paid
    # prepaid payments made during the year (asset in the unadjusted TB; amortised by close journal J2)
    prepaids = [{"entity": "P", "item": "Insurance renewal", "amount": 12.0, "months": 12, "elapsed": 7},
                {"entity": "P", "item": "Software licences", "amount": 8.4, "months": 24, "elapsed": 9},
                {"entity": "S1", "item": "Warehouse rent in advance", "amount": 4.8, "months": 6, "elapsed": 2},
                {"entity": "S2", "item": "Business rates", "amount": 2.4, "months": 12, "elapsed": 10},
                {"entity": "S3", "item": "Maintenance contract", "amount": 3.6, "months": 12, "elapsed": 4}]
    for p in prepaids:
        led.post(p["entity"], 1300, 1000, p["amount"])
    accruals = [{"entity": "P", "item": "Unbilled freight", "amount": 3.1},
                {"entity": "P", "item": "Audit fee", "amount": 1.2},
                {"entity": "S1", "item": "Utilities", "amount": 0.9},
                {"entity": "S2", "item": "Agency staff", "amount": 0.7},
                {"entity": "S3", "item": "Contractor hours", "amount": 1.5}]
    # cut-off error at P: goods shipped after year end were invoiced and relieved from stock in December
    led.post("P", 1100, 4000, cutoff["revenue"]); led.post("P", 5000, 1200, cutoff["cost"])
    # intercompany sales P -> S1
    led.post("P", 1150, 4100, ic_sales); led.post("P", 5000, 1200, ic_sales * (1 - ic_margin))
    led.post("S1", 1200, 2050, ic_sales)
    led.post("S1", 5000, 1200, s1_ic_cogs)
    s1_paid = r3(20.0 + ic_sales - u(14, 18))                             # pays opening balance and most of the year
    led.post("S1", 2050, 1000, s1_paid)
    led.post("P", 1000, 1150, s1_paid - in_transit)
    # management fee S2 -> P, settled in cash during the year at the average rate
    led.post("S2", 6100, 1000, fee_gbp)
    led.post("P", 1000, 4200, fee_gbp * fx["avg"])
    # intercompany loan P -> S3
    led.post("P", 1700, 1000, loan_advance); led.post("S3", 1000, 2700, loan_advance)
    ic_int = r3(50.0 * rates["ic_loan"])
    led.post("S3", 7100, 1000, ic_int); led.post("P", 1000, 4300, ic_int)
    # dividends
    led.post("S3", 3200, 1000, div_s3); led.post("P", 1000, 4500, div_s3 * own["S3"])
    led.post("P", 3200, 1000, 30.0)
    led.post("P", 1000, 1650, assoc_div)
    for e in ENTITIES:
        tot = sum(led.bal[e].values())
        assert abs(tot) < 1e-6, f"{e} TB out by {tot}"
        assert led.bal[e][1000] > 0 and led.bal[e][1200] > 0, f"{e}: cash or inventory negative"
    tb = {e: {k: r3(v) for k, v in led.bal[e].items() if abs(v) > 1e-12} for e in ENTITIES}
    for e in ENTITIES:
        tb[e][3100] -= sum(tb[e].values())   # absorb float dust (<1e-9) so each TB sums to zero exactly

    # bank statements: GL cash after close journals, plus uncleared items
    bank = {}
    for e in ENTITIES:
        gl = tb[e][1000] + (in_transit if e == "P" else 0.0)
        out_chq = u(1.0, 3.0) * (1 if e != "S2" else 0.3)
        dep_transit = in_transit if e == "P" else 0.0
        bank[e] = {"statement": r3(gl + out_chq - dep_transit), "outstanding_cheques": out_chq, "deposits_in_transit": dep_transit}

    # S2 translation history: opening retained earnings in USD and the CTA built up in earlier years
    s2o = opening["S2"]
    na_open = -(s2o[3000] + s2o[3100])                                    # net assets (GBP) = share capital + RE
    re_open_usd = r3(-s2o[3100] * 1.3700)                                 # earlier earnings at historical average rates
    cta_open = na_open * fx["open"] - sc["S2"] * fx["hist"] - re_open_usd   # exact, so the CTA roll-forward ties

    close = {
        "fx": fx, "own": own, "acquisition_s3": acq, "lives": lives, "tax_rates": tax_rates,
        "ic": {"sales": ic_sales, "margin": ic_margin, "s1_ic_inventory": s1_ic_inventory, "s1_ic_purchases": ic_sales,
               "in_transit": in_transit, "fee_gbp": fee_gbp, "loan_rate": rates["ic_loan"]},
        "associate": {"net_income": assoc_ni, "dividends": assoc_div},
        "cutoff": cutoff, "prepaids": prepaids, "accruals": accruals, "bank": bank,
        "s2_history": {"re_open_usd": re_open_usd, "cta_open": cta_open},
    }
    return {"opening": opening, "tb": tb, "close": close}


def write(g: dict, out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "accounts.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["code", "name", "type", "fs_line", "cf_line", "taxable", "fx_basis"])
        w.writerows([(*a, taxable(a[0], a[2]), fx_basis(a[0], a[2])) for a in ACCOUNTS])
    for name, table in (("opening.csv", g["opening"]), ("tb_unadjusted.csv", g["tb"])):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["code", *ENTITIES])
            for code in CODES:
                w.writerow([code, *(repr(float(table[e].get(code, 0.0))) for e in ENTITIES)])
    (out / "close.yaml").write_text("# Close inputs for the synthetic group (generated by ledgerline.data.group, seed %d).\n" % SEED
                                    + yaml.safe_dump(g["close"], sort_keys=False))


def load(base: Path = OUT) -> dict:
    def table(name):
        with open(base / name) as f:
            r = csv.reader(f)
            head = next(r)
            out = {e: {} for e in head[1:]}
            for row in r:
                for e, v in zip(head[1:], row[1:]):
                    out[e][int(row[0])] = float(v)
            return out
    with open(base / "accounts.csv") as f:
        r = csv.DictReader(f)
        accounts = [(int(x["code"]), x["name"], x["type"], x["fs_line"], x["cf_line"], int(x["taxable"]), x["fx_basis"])
                    for x in r]
    return {"accounts": accounts, "opening": table("opening.csv"), "tb": table("tb_unadjusted.csv"),
            "close": yaml.safe_load((base / "close.yaml").read_text())}


if __name__ == "__main__":
    write(generate())
    print("wrote", OUT.relative_to(REPO))
    sys.exit(0)
