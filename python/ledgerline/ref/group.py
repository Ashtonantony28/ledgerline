"""Independent reference for workbook 05, close and consolidation (docs/models/group.md).

Signs follow the trial balance: debit positive, credit negative.
"""
from __future__ import annotations

from collections import defaultdict

ENTITIES = ["P", "S1", "S2", "S3"]
IS_TYPES = ("R", "X")
NON_TAXABLE = (4400, 4500, 8000, 9000)  # equity-method income and dividends are outside the tax base (judgement)
CF_LINES = {"cfo": ["ni", "da", "assoc", "wc_receivables", "wc_ic", "wc_inventory", "wc_payables", "wc_other"],
            "cfi": ["capex", "inv_subs", "ic_loan_rec"], "cff": ["debt", "ic_loan_pay", "equity", "dividends"]}
FS_BS = ["cash", "receivables", "ic_receivables", "inventory", "prepaids", "ppe", "inv_subs", "inv_assoc", "ic_loan_rec",
         "goodwill", "payables", "ic_payables", "accrued", "tax_payable", "debt", "ic_loan_pay", "share_capital", "re_open",
         "dividends", "cta", "nci"]
FS_IS = ["revenue", "ic_revenue", "fee_income", "ic_int_income", "assoc_income", "div_income", "cogs", "opex", "fee_expense",
         "depreciation", "interest", "ic_int_expense", "tax", "nci_income"]


def journals(g: dict) -> list[tuple[str, str, int, float]]:
    """Close journals: (id, entity, account, amount). Each id balances."""
    c, tb, op = g["close"], g["tb"], g["opening"]
    out = []

    def je(jid, e, pairs):
        out.extend((jid, e, code, amt) for code, amt in pairs)

    for e in ENTITIES:  # J1 depreciation: opening cost plus half of this year's additions, straight line
        capex = tb[e][1500] - op[e][1500]
        d = (op[e][1500] + 0.5 * capex) / c["lives"][e]
        je(f"J1-{e}", e, [(6200, d), (1510, -d)])
    for k, p in enumerate(c["prepaids"], 1):  # J2 prepaid amortisation
        a = p["amount"] * p["elapsed"] / p["months"]
        je(f"J2-{k}", p["entity"], [(6000, a), (1300, -a)])
    for k, a in enumerate(c["accruals"], 1):  # J3 accruals for unbilled costs
        je(f"J3-{k}", a["entity"], [(6000, a["amount"]), (2100, -a["amount"])])
    co = c["cutoff"]  # J4 revenue cut-off at P
    je("J4", "P", [(4000, co["revenue"]), (1100, -co["revenue"]), (1200, co["cost"]), (5000, -co["cost"])])
    x = c["ic"]["in_transit"]  # J6 intercompany cash in transit
    je("J6", "P", [(1000, x), (1150, -x)])
    s = c["own"]["assoc"] * c["associate"]["net_income"]  # J7 equity-method share of associate income
    je("J7", "P", [(1650, s), (4400, -s)])
    pre = defaultdict(float)
    for _, e, code, amt in out:
        pre[(e, code)] += amt
    for e in ENTITIES:  # J5 income tax on adjusted pre-tax income
        base = -sum(tb[e].get(code, 0.0) + pre[(e, code)] for code, _, t, *_ in g["accounts"]
                    if t in IS_TYPES and code not in NON_TAXABLE)
        t_ = c["tax_rates"][e] * max(0.0, base)
        je(f"J5-{e}", e, [(8000, t_), (2200, -t_)])
    return out


def run(g: dict) -> dict:
    c, tb, op, accts = g["close"], g["tb"], g["opening"], g["accounts"]
    typ = {a[0]: a[2] for a in accts}
    fs = {a[0]: a[3] for a in accts}
    cfl = {a[0]: a[4] for a in accts}
    fx = c["fx"]
    r: dict = {}
    jl = journals(g)
    adj = {e: {code: tb[e].get(code, 0.0) for code in typ} for e in ENTITIES}
    for _, e, code, amt in jl:
        adj[e][code] += amt
    r["adj"] = adj
    r["tax"] = {e: sum(a for jid, ee, code, a in jl if ee == e and code == 8000) for e in ENTITIES}
    r["ni"] = {e: -sum(v for code, v in adj[e].items() if typ[code] in IS_TYPES) for e in ENTITIES}
    r["tb_sum"] = {e: sum(adj[e].values()) for e in ENTITIES}

    # ---------------------------------------------------------------- translation (S2, current-rate method)
    usd = {}
    for code, v in adj["S2"].items():
        t = typ[code]
        if code == 3000:
            usd[code] = v * fx["hist"]
        elif code == 3100:
            usd[code] = -c["s2_history"]["re_open_usd"]
        elif t in ("A", "L"):
            usd[code] = v * fx["close"]
        else:  # revenue, expenses, dividends at the average rate
            usd[code] = v * fx["avg"]
    usd[3300] = -sum(v for k, v in usd.items() if k != 3300)   # CTA is the balancing figure
    r["s2_usd"] = usd
    r["cta_plug"] = -usd[3300]
    na_open = -(op["S2"].get(3000, 0.0) + op["S2"].get(3100, 0.0))
    r["cta_analytic"] = (c["s2_history"]["cta_open"] + na_open * (fx["close"] - fx["open"])
                         + r["ni"]["S2"] * (fx["close"] - fx["avg"]))  # S2 pays no dividends

    # ---------------------------------------------------------------- consolidation worksheet by FS line (USD)
    lines = FS_BS + FS_IS
    col = {e: defaultdict(float) for e in ENTITIES}
    for e in ENTITIES:
        src = usd if e == "S2" else adj[e]
        for code, v in src.items():
            col[e][fs[code]] += v
    own, acq = c["own"]["S3"], c["acquisition_s3"]
    nci_pct = 1 - own
    sc1, sc2, sc3 = -adj["S1"][3000], -usd[3000], -adj["S3"][3000]
    re_open3, div3, ni3 = -adj["S3"][3100], adj["S3"][3200], r["ni"]["S3"]
    gw = acq["consideration"] + acq["nci_fv"] - sc3 - acq["re_acq"]
    urp = c["ic"]["s1_ic_inventory"] * c["ic"]["margin"]
    X, L = adj["P"][1150], adj["P"][1700]
    S, F, I = -adj["P"][4100], -adj["P"][4200], -adj["P"][4300]
    elims = {
        "E1": [("share_capital", sc1), ("inv_subs", -sc1)],
        "E2": [("share_capital", sc2), ("inv_subs", -sc2)],
        "E3": [("share_capital", sc3), ("re_open", acq["re_acq"]), ("goodwill", gw), ("inv_subs", -acq["consideration"]),
               ("nci", -acq["nci_fv"])],
        "E4": [("re_open", nci_pct * (re_open3 - acq["re_acq"])), ("nci", -nci_pct * (re_open3 - acq["re_acq"]))],
        "E5": [("nci_income", nci_pct * ni3), ("nci", -nci_pct * ni3)],
        "E6": [("div_income", own * div3), ("nci", nci_pct * div3), ("dividends", -div3)],
        "E7": [("ic_payables", X), ("ic_receivables", -X)],
        "E8": [("ic_loan_pay", L), ("ic_loan_rec", -L)],
        "E9": [("ic_revenue", S), ("cogs", -S)],
        "E10": [("cogs", urp), ("inventory", -urp)],
        "E11": [("fee_income", F), ("fee_expense", -F)],
        "E12": [("ic_int_income", I), ("ic_int_expense", -I)],
    }
    el = defaultdict(float)
    for pairs in elims.values():
        for line, amt in pairs:
            el[line] += amt
    r["elim_sums"] = {k: sum(a for _, a in v) for k, v in elims.items()}
    r["goodwill"], r["urp"] = gw, urp
    cons = {ln: sum(col[e][ln] for e in ENTITIES) + el[ln] for ln in lines}
    r["col"], r["elim"], r["cons"] = col, dict(el), cons

    # ---------------------------------------------------------------- statements
    st = {}
    for ln in FS_IS:
        st[ln] = -cons[ln] if ln in ("revenue", "ic_revenue", "fee_income", "ic_int_income", "assoc_income", "div_income") else cons[ln]
    st["ni_total"] = -sum(cons[ln] for ln in FS_IS if ln != "nci_income")
    st["ni_nci"] = cons["nci_income"]
    st["ni_parent"] = st["ni_total"] - st["ni_nci"]
    assets = ["cash", "receivables", "ic_receivables", "inventory", "prepaids", "ppe", "inv_subs", "inv_assoc", "ic_loan_rec", "goodwill"]
    liabs = ["payables", "ic_payables", "accrued", "tax_payable", "debt", "ic_loan_pay"]
    st["total_assets"] = sum(cons[a] for a in assets)
    st["total_liabilities"] = -sum(cons[a] for a in liabs)
    st["share_capital"] = -cons["share_capital"]
    st["re_open"] = -cons["re_open"]
    st["div_parent"] = -cons["dividends"]  # shown as a deduction in the roll-forward
    st["re_close"] = st["re_open"] + st["ni_parent"] + st["div_parent"]
    st["cta"] = -cons["cta"]
    st["nci"] = -cons["nci"]
    st["total_equity"] = st["share_capital"] + st["re_close"] + st["cta"] + st["nci"]
    na3 = sum(v for code, v in adj["S3"].items() if typ[code] in ("A", "L"))
    st["nci_check"] = nci_pct * na3 + (acq["nci_fv"] - nci_pct * (sc3 + acq["re_acq"]))
    r["st"] = st

    # ---------------------------------------------------------------- cash flow (indirect, built from the TBs)
    cf = {e: defaultdict(float) for e in ENTITIES}
    for e in ENTITIES:
        cf[e]["ni"] = r["ni"][e]
        for code, t in typ.items():
            if t in ("A", "L", "E") and cfl[code] not in ("cash", "none"):
                cf[e][cfl[code]] += -(adj[e][code] - op[e].get(code, 0.0))
    cf_usd = {e: {k: v * (fx["avg"] if e == "S2" else 1.0) for k, v in cf[e].items()} for e in ENTITIES}
    dL = adj["P"][1700] - op["P"].get(1700, 0.0)
    cf_el = defaultdict(float, {"ni": -(own * div3 + urp), "wc_inventory": urp, "ic_loan_rec": dL, "ic_loan_pay": -dL,
                                "dividends": own * div3})
    all_lines = [x for v in CF_LINES.values() for x in v]
    cons_cf = {k: sum(cf_usd[e].get(k, 0.0) for e in ENTITIES) + cf_el[k] for k in all_lines}
    for sec, ks in CF_LINES.items():
        cons_cf[sec] = sum(cons_cf[k] for k in ks)
        for e in ENTITIES:
            cf[e][sec] = sum(cf[e].get(k, 0.0) for k in ks)
    s2c_o, s2c_c = op["S2"][1000], adj["S2"][1000]
    cons_cf["fx"] = s2c_c * fx["close"] - s2c_o * fx["open"] - (s2c_c - s2c_o) * fx["avg"]
    cons_cf["net"] = cons_cf["cfo"] + cons_cf["cfi"] + cons_cf["cff"] + cons_cf["fx"]
    cash_rate = lambda e, which: fx[which] if e == "S2" else 1.0
    cons_cf["cash_open"] = sum(op[e][1000] * cash_rate(e, "open") for e in ENTITIES)
    cons_cf["cash_close"] = sum(adj[e][1000] * cash_rate(e, "close") for e in ENTITIES)
    r["cf"], r["cf_elim"], r["cons_cf"] = cf, dict(cf_el), cons_cf
    r["entity_cf_check"] = {e: cf[e]["cfo"] + cf[e]["cfi"] + cf[e]["cff"] - (adj[e][1000] - op[e][1000]) for e in ENTITIES}

    # ---------------------------------------------------------------- reconciliations
    bank = c["bank"]
    r["bank_diff"] = {e: bank[e]["statement"] - bank[e]["outstanding_cheques"] + bank[e]["deposits_in_transit"] - adj[e][1000]
                      for e in ENTITIES}
    ic = c["ic"]
    r["ic_recs"] = {
        "trade_unadjusted": tb["P"][1150] + tb["S1"][2050],
        "trade": adj["P"][1150] + adj["S1"][2050],
        "loan": adj["P"][1700] + adj["S3"][2700],
        "sales": -adj["P"][4100] - ic["s1_ic_purchases"],
        "fee": -adj["P"][4200] - adj["S2"][6100] * fx["avg"],
        "interest": -adj["P"][4300] - adj["S3"][7100],
        "dividend": -adj["P"][4500] - own * adj["S3"][3200],
    }
    return r
