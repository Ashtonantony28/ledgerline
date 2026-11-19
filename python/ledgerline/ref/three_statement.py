"""Independent Python reference for the three-statement operating model (the golden model).

Written from the model specification in docs/models/three-statement.md, not from the
workbook's formulas (ADR 0005). Inputs are the shared `Inputs`; everything else is computed
here. Units: $m, shares in millions, $/share for price and EPS.
"""
from __future__ import annotations

from ..models.assumptions import Inputs

FLAT_ASSETS = ("st_investments", "op_lease_rou", "goodwill", "intangibles", "other_nc_assets")
MAX_ITER = 500
TOL = 1e-10


def opening(inp: Inputs) -> dict[str, float]:
    """Last historical year in model units, mapped onto the forecast balance-sheet lines."""
    last = lambda k: inp.h(k)[-1]
    prev = lambda k: inp.h(k)[-2]
    o = {k: last(k) for k in ("cash", "receivables", "inventory", "other_current_assets", "ppe_net",
                               "accounts_payable", "other_nc_liabilities", "parent_equity", "nci_equity",
                               "shares_diluted", "revenue", "stores", *FLAT_ASSETS)}
    o["ocl"] = sum(last(k) for k in ("accrued_liabilities", "employee_liabilities", "deferred_revenue",
                                     "other_current_liabilities"))
    o["op_lease_liab"] = last("op_lease_liab_current") + last("op_lease_liab_noncurrent")
    o["debt"] = last("current_debt") + last("lt_debt") + last("short_term_debt")
    o["revolver"] = 0.0
    o["rev_per_store"] = last("revenue") / ((last("stores") + prev("stores")) / 2)
    o["share_price"] = inp.share_price
    return o


def run(inp: Inputs) -> dict[str, list[float]]:
    """Forecast years only. Returns per-line lists of length n_fcst."""
    o = opening(inp)
    d = {k: inp.live(k) for k in inp.drivers}
    c = inp.constants
    out: dict[str, list[float]] = {}
    prev = dict(o)
    for t in range(inp.n_fcst):
        r = _year(prev, {k: v[t] for k, v in d.items()}, c, inp.maturities[t], inp.circ)
        for k, v in r.items():
            out.setdefault(k, []).append(v)
        prev = r
    return out


def _year(p: dict, d: dict, c: dict, maturity: float, circ: int) -> dict[str, float]:
    y: dict[str, float] = {}
    y["stores"] = p["stores"] + d["store_openings"]
    y["avg_stores"] = (y["stores"] + p["stores"]) / 2
    y["rev_per_store"] = p["rev_per_store"] * (1 + d["sales_per_store_growth"])
    y["revenue"] = y["avg_stores"] * y["rev_per_store"]
    y["cogs"] = y["revenue"] * (1 - d["gross_margin"])
    y["gross_profit"] = y["revenue"] - y["cogs"]
    y["sga"] = y["revenue"] * d["sga_pct"]
    y["other_opex"] = y["revenue"] * d["other_opex_pct"]
    y["operating_income"] = y["gross_profit"] - y["sga"] - y["other_opex"]
    y["da"] = d["da_pct_ppe"] * p["ppe_net"]
    y["ebitda"] = y["operating_income"] + y["da"]
    y["capex"] = y["revenue"] * d["capex_pct"]
    y["ppe_net"] = p["ppe_net"] + y["capex"] - y["da"]
    y["receivables"] = y["revenue"] * d["receivable_days"] / c["days_in_year"]
    y["inventory"] = y["cogs"] * d["inventory_days"] / c["days_in_year"]
    y["accounts_payable"] = y["cogs"] * d["payable_days"] / c["days_in_year"]
    y["other_current_assets"] = y["revenue"] * d["oca_pct"]
    y["ocl"] = y["revenue"] * d["ocl_pct"]
    y["sbc"] = y["revenue"] * d["sbc_pct"]
    y["repay"] = min(maturity, p["debt"])
    y["issue"] = maturity * c["refinance_pct"]
    y["debt"] = p["debt"] - y["repay"] + y["issue"]
    for k in FLAT_ASSETS + ("op_lease_liab", "other_nc_liabilities", "nci_equity"):
        y[k] = p[k]
    d_nwc_assets = (y["receivables"] - p["receivables"]) + (y["inventory"] - p["inventory"]) + \
                   (y["other_current_assets"] - p["other_current_assets"])
    d_nwc_liabs = (y["accounts_payable"] - p["accounts_payable"]) + (y["ocl"] - p["ocl"])
    y["change_nwc"] = d_nwc_liabs - d_nwc_assets

    # Interest: opening balances (circ=0) or average balances solved as a fixed point (circ=1).
    cash_end, rev_end = p["cash"], p["revolver"]
    for _ in range(MAX_ITER):
        debt_base = (p["debt"] + y["debt"]) / 2 if circ else p["debt"]
        rev_base = (p["revolver"] + rev_end) / 2 if circ else p["revolver"]
        cash_base = (p["cash"] + cash_end) / 2 if circ else p["cash"]
        y["interest_expense"] = d["debt_rate"] * debt_base + c["revolver_rate"] * rev_base
        y["interest_income"] = d["cash_rate"] * cash_base
        y["pretax_income"] = y["operating_income"] - y["interest_expense"] + y["interest_income"]
        y["income_tax"] = y["pretax_income"] * d["tax_rate"]
        y["net_income"] = y["pretax_income"] - y["income_tax"]
        y["dividends"] = -max(y["net_income"], 0.0) * d["payout_ratio"]
        y["buybacks"] = -max(y["net_income"], 0.0) * d["buyback_pct"]
        y["cfo"] = y["net_income"] + y["da"] + y["sbc"] + y["change_nwc"]
        y["cfi"] = -y["capex"]
        avail = p["cash"] + y["cfo"] + y["cfi"] + y["dividends"] + y["buybacks"] + y["issue"] - y["repay"]
        y["special_dividends"] = -max(0.0, avail - c["max_cash"])
        pre = avail + y["special_dividends"]
        y["cash_pre_revolver"] = pre
        y["revolver_draw"] = min(max(c["min_cash"] - pre, -p["revolver"]), c["revolver_capacity"] - p["revolver"])
        new_rev, new_cash = p["revolver"] + y["revolver_draw"], pre + y["revolver_draw"]
        converged = abs(new_cash - cash_end) < TOL and abs(new_rev - rev_end) < TOL
        cash_end, rev_end = new_cash, new_rev
        if not circ or converged:
            break
    y["revolver"], y["cash"] = rev_end, cash_end
    y["cff"] = y["dividends"] + y["special_dividends"] + y["buybacks"] + y["issue"] - y["repay"] + y["revolver_draw"]
    y["net_change_cash"] = y["cfo"] + y["cfi"] + y["cff"]
    y["parent_equity"] = p["parent_equity"] + y["net_income"] + y["dividends"] + y["special_dividends"] + y["buybacks"] + y["sbc"]
    y["share_price"] = p["share_price"] * (1 + d["share_price_growth"])
    y["shares_diluted"] = p["shares_diluted"] + (y["sbc"] + y["buybacks"]) / y["share_price"]
    y["eps_diluted"] = y["net_income"] / y["shares_diluted"]
    y["total_assets"] = (y["cash"] + y["st_investments"] + y["receivables"] + y["inventory"] + y["other_current_assets"]
                         + y["ppe_net"] + y["op_lease_rou"] + y["goodwill"] + y["intangibles"] + y["other_nc_assets"])
    y["total_liabilities"] = (y["accounts_payable"] + y["ocl"] + y["debt"] + y["revolver"] + y["op_lease_liab"]
                              + y["other_nc_liabilities"])
    y["total_equity"] = y["parent_equity"] + y["nci_equity"]
    y["balance_check"] = y["total_assets"] - y["total_liabilities"] - y["total_equity"]
    return y
