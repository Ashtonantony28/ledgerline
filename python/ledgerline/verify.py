"""Compare a recalculated workbook against its Python reference (tolerances: ADR 0005).

Currency lines: |workbook - reference| <= $0.01 (model units are $m, so 1e-8).
Per-share and ratio lines: relative error <= 1e-9 (absolute 1e-9 near zero).
"""
from __future__ import annotations

from dataclasses import dataclass

TOL_USD_M = 0.01 / 1e6
TOL_REL = 1e-9

THREE_STATEMENT_OUTPUTS = [  # (sheet, row key, reference key, kind)
    ("IS", "revenue", "revenue", "usd"), ("IS", "cogs", "cogs", "usd"), ("IS", "sga", "sga", "usd"),
    ("IS", "operating_income", "operating_income", "usd"), ("IS", "interest_expense", "interest_expense", "usd"),
    ("IS", "other_nonop_income", "interest_income", "usd"), ("IS", "pretax_income", "pretax_income", "usd"),
    ("IS", "income_tax", "income_tax", "usd"), ("IS", "net_income", "net_income", "usd"),
    ("IS", "shares_diluted", "shares_diluted", "ratio"), ("IS", "eps_diluted", "eps_diluted", "ratio"),
    ("IS", "ebitda", "ebitda", "usd"),
    ("BS", "cash", "cash", "usd"), ("BS", "receivables", "receivables", "usd"), ("BS", "inventory", "inventory", "usd"),
    ("BS", "ppe_net", "ppe_net", "usd"), ("BS", "total_assets", "total_assets", "usd"),
    ("BS", "accounts_payable", "accounts_payable", "usd"), ("BS", "ocl", "ocl", "usd"), ("BS", "debt", "debt", "usd"),
    ("BS", "revolver", "revolver", "usd"), ("BS", "total_liabilities", "total_liabilities", "usd"),
    ("BS", "parent_equity", "parent_equity", "usd"),
    ("CF", "cfo", "cfo", "usd"), ("CF", "cfi", "cfi", "usd"), ("CF", "cff", "cff", "usd"),
    ("CF", "dividends", "dividends", "usd"), ("CF", "special_dividends", "special_dividends", "usd"),
    ("CF", "buybacks", "buybacks", "usd"), ("CF", "net_change_cash", "net_change_cash", "usd"),
]

MNA_OUTPUTS = [("Standalone", k, k, "usd") for k in ("dks_revenue", "dks_ebitda", "dks_pretax", "dks_ni", "fl_revenue", "fl_ni")] + \
    [("Standalone", "eps_sa", "eps_sa", "ratio")] + \
    [("ProForma", k, k, "usd") for k in ("syn", "dep_step", "amort_int", "lease_amort", "notes_accr", "new_int", "iss_amort",
                                        "lost_int", "adj_pretax", "pf_ni_adj", "close_items", "pf_ni_gaap", "breakeven_syn", "breakeven_fl_ni",
                                        "pf_ebitda", "pf_ni_pre_fin")] + \
    [("ProForma", k, k, "ratio") for k in ("pf_shares", "eps_adj", "eps_gaap", "acc_adj", "acc_gaap", "pf_leverage")]


@dataclass
class Mismatch:
    sheet: str
    key: str
    period: int
    workbook: object
    reference: float

    def __str__(self) -> str:
        return f"{self.sheet}.{self.key}[{self.period}]: workbook={self.workbook!r} reference={self.reference!r}"


def close(a, b: float, kind: str) -> bool:
    if not isinstance(a, (int, float)):
        return False
    if kind == "usd":
        return abs(a - b) <= TOL_USD_M
    return abs(a - b) <= max(TOL_REL * abs(b), TOL_REL)


def compare(values, ref: dict[str, list[float]], outputs) -> list[Mismatch]:
    bad = []
    for sheet, key, rkey, kind in outputs:
        got = values.fcst(sheet, key)
        for t, (a, b) in enumerate(zip(got, ref[rkey])):
            if not close(a, b, kind):
                bad.append(Mismatch(sheet, key, t, a, b))
    return bad


GROUP_ENT = ["P", "S1", "S2", "S3"]
GROUP_TOL = 0.01  # ADR 0005: $0.01 on currency


def group_expected(r: dict) -> dict[str, float]:
    """Address-map key -> reference value."""
    x = {}
    for e in GROUP_ENT:
        for code, v in r["adj"][e].items():
            x[f"adj_{e}_{code}"] = v
        x[f"tax_{e}"] = r["tax"][e]
        x[f"ni_{e}"] = r["ni"][e]
        x[f"TB_Adj_sum_{e}"] = r["tb_sum"][e]
        x[f"bank_diff_{e}"] = r["bank_diff"][e]
        x[f"cf_check_{e}"] = r["entity_cf_check"][e]
        for k, v in r["cf"][e].items():
            x[f"cf_{e}_{k}"] = v
    for code, v in r["s2_usd"].items():
        x[f"usd_{code}"] = v
    x["cta_plug"], x["cta_analytic"] = r["cta_plug"], r["cta_analytic"]
    x["goodwill"], x["urp"] = r["goodwill"], r["urp"]
    for k, v in r["cons"].items():
        x[f"cons_{k}"] = v
    for k, v in r["st"].items():
        if k != "nci_income":  # shown as st_ni_nci
            x[f"st_{k}"] = v
    for k, v in r["cons_cf"].items():
        x[f"ccf_{k}"] = v
    for k, v in r["ic_recs"].items():
        x[{"trade_unadjusted": "ic_trade_unadj"}.get(k, f"ic_{k}")] = v
    return x


def group_compare(get, addr: dict, exp: dict) -> list[str]:
    bad, missing = [], [k for k in exp if k not in addr]
    for k, v in exp.items():
        if k in addr:
            a = get(*addr[k])
            if a is None or abs(float(a) - v) > GROUP_TOL:
                bad.append(f"{k} {addr[k]}: workbook {a} vs ref {v}")
    return bad + [f"no cell for {k}" for k in missing]


FPA_PRODUCTS = ["Core", "Premium", "Services"]
FPA_DEPTS = ["SalesMarketing", "Operations", "GA"]
FPA_OUTPUTS = (  # full-timeline series: (sheet, row key, reference key, kind)
    [("PnL", k, k, "usd") for k in ("rev", "cogs", "gp", "opex", "ebitda", "capex", "dep", "ebit", "tax", "nwc", "dnwc", "fcf", "cash")]
    + [("PnL", f"{x}_{p}", f"{x}_{p}", "usd") for p in FPA_PRODUCTS for x in ("rev", "cogs")]
    + [("PnL", f"{x}_{d}", f"{x}_{d}", "usd") for d in FPA_DEPTS for x in ("people", "np", "opex")]
    + [("Drivers", f"{x}_{p}", f"{x}_{p}", "ratio") for p in FPA_PRODUCTS for x in ("vol", "price", "uc")]
    + [("Drivers", f"{x}_{d}", f"{x}_{d}", "ratio") for d in FPA_DEPTS for x in ("heads", "cph")]
    + [("Budget", k, k, "usd") for k in ("brev", "bcogs", "bgp", "bopex", "bebitda")]
    + [("Budget", f"{x}_{p}", f"{x}_{p}", "usd") for p in FPA_PRODUCTS for x in ("brev", "bcogs")]
    + [("Budget", f"bvol_{p}", f"bvol_{p}", "ratio") for p in FPA_PRODUCTS]
    + [("Budget", f"{x}_{d}", f"{x}_{d}", "usd") for d in FPA_DEPTS for x in ("bpeople", "bnp", "bopex")]
    + [("Budget", f"bheads_{d}", f"bheads_{d}", "ratio") for d in FPA_DEPTS]
)
FPA_BRIDGE = (["rev_actual", "rev_budget", "price", "rev_volume", "rev_mix", "cost", "gp_volume", "gp_mix", "heads", "rate", "np",
               "opex_var", "ebitda_budget", "ebitda_bridge", "ebitda_actual"]
              + [f"{x}_{d}" for d in FPA_DEPTS for x in ("heads", "rate", "np")])
FPA_CONSTS = ([("Variance", f"{s}_{k}", (s, k), "usd") for s in ("ytd", "fy") for k in FPA_BRIDGE]
              + [("PnL", k, k, "usd") for k in ("min_cash_fc", "headroom")]
              + [("Drivers", f"rr_{p}", f"rr_{p}", "ratio") for p in FPA_PRODUCTS]
              + [("Drivers", "np_sm_pct", "np_sm_pct", "ratio")]
              + [("Accuracy", k, k, "ratio") for k in ("mape", "bias")] + [("Accuracy", "q4_change", "q4_change", "usd")])


def fpa_compare(values, ref: dict) -> list[str]:
    """Every FP&A output, history and forecast columns, plus the bridge and summary constants."""
    bad = []
    for sheet, key, rkey, kind in FPA_OUTPUTS:
        for t, (a, b) in enumerate(zip(values.series(sheet, key), ref[rkey])):
            if not close(a, b, kind):
                bad.append(f"{sheet}.{key}[{t}] {a} vs {b}")
    for sheet, key, rkey, kind in FPA_CONSTS:
        b = ref[rkey[0]][rkey[1]] if isinstance(rkey, tuple) else ref[rkey]
        if not close(values.const(sheet, key), b, kind):
            bad.append(f"{sheet}.{key} {values.const(sheet, key)} vs {b}")
    return bad
