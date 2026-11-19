"""Independent reference for workbook 03, the LBO (docs/models/lbo.md)."""
from __future__ import annotations

from ..models.lbo_inputs import LBOInputs


def irr(flows: list[float], lo: float = -0.99, hi: float = 10.0) -> float:
    """IRR by bisection on NPV (flows at integer years from 0)."""
    npv = lambda r: sum(cf / (1 + r) ** t for t, cf in enumerate(flows))
    f_lo = npv(lo)
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def transaction(inp: LBOInputs) -> dict:
    t, h = inp.tx, inp.h
    r = {}
    r["uses"] = (t["cash_consideration"] + t["rollover_equity"] + t["debt_repaid"] + t["financing_fees"] + t["rcf_fees"]
                 + t["transaction_costs"])
    r["sources_ex_cash"] = t["tl_total"] + t["ssn"] + t["pik_notes"] + t["sponsor_equity"] + t["rollover_equity"]
    r["cash_used"] = r["uses"] - r["sources_ex_cash"]
    r["cash0"] = h("cash")[-1] - r["cash_used"]
    r["tl_eur"] = t["tl_total"] - t["tl_usd"]
    debt_pre = h("short_term_debt")[-1] + h("current_debt")[-1] + h("lt_debt")[-1]
    r["existing_debt"] = debt_pre - t["debt_repaid"]
    r["nci0"] = h("nci_equity")[-1] + h("temp_equity")[-1]
    r["ebitda0"] = h("operating_income")[-1] + h("da")[-1]
    r["E0"] = t["sponsor_equity"] + t["rollover_equity"]
    r["claims0"] = t["tl_total"] + t["ssn"] + t["pik_notes"] + r["existing_debt"] - r["cash0"] + r["nci0"]
    r["entry_ev"] = r["E0"] + r["claims0"]
    r["entry_mult"] = r["entry_ev"] / r["ebitda0"]
    r["headline_ev"] = (t["cash_consideration"] + t["rollover_equity"] + debt_pre - h("cash")[-1] - h("st_investments")[-1]
                        + r["nci0"])
    r["headline_mult"] = r["headline_ev"] / r["ebitda0"]
    r["sponsor_share"] = t["sponsor_equity"] / r["E0"]
    r["debt_at_close"] = t["tl_total"] + t["ssn"] + t["pik_notes"] + r["existing_debt"]
    r["leverage_at_close"] = r["debt_at_close"] / r["ebitda0"]
    return r


def run(inp: LBOInputs) -> dict:
    t, j = inp.tx, inp.j
    tr = transaction(inp)
    n = inp.n_fcst
    d = {k: inp.live(k) for k in inp.drivers}
    out: dict = {k: [] for k in (
        "revenue", "ebitda", "da", "ebit", "capex", "nwc", "change_nwc", "int_tlu", "int_tle", "int_ssn", "int_pik",
        "pik_accrued", "int_rcf", "int_existing", "interest_total", "cash_interest", "taxes", "ni_total", "nci_dist", "lfcf",
        "amort_u", "amort_e", "cash_pre", "rcf_draw", "excess", "sweep", "sweep_u", "sweep_e", "tlu", "tle", "ssn", "pik",
        "rcf", "existing", "cash", "total_debt", "net_debt", "nci_claim", "lev_1l", "lev_total", "icr", "headroom",
        "exit_ev", "exit_equity", "investor_equity")}
    p = {"revenue": inp.h("revenue")[-1], "nwc": inp.nwc_hist()[-1], "tlu": t["tl_usd"], "tle": tr["tl_eur"],
         "ssn": t["ssn"], "pik": t["pik_notes"], "rcf": 0.0, "existing": tr["existing_debt"], "cash": tr["cash0"]}
    for k in range(n):
        y = {}
        y["revenue"] = p["revenue"] * (1 + d["revenue_growth"][k])
        y["ebitda"] = y["revenue"] * d["ebitda_margin"][k]
        y["da"] = y["revenue"] * d["da_pct"][k]
        y["ebit"] = y["ebitda"] - y["da"]
        y["capex"] = y["revenue"] * d["capex_pct"][k]
        y["nwc"] = y["revenue"] * d["nwc_pct"][k]
        y["change_nwc"] = p["nwc"] - y["nwc"]
        sofr, eur, tog = inp.rates["sofr"][k], inp.rates["euribor"][k], inp.rates["pik_toggle"][k]
        y["int_tlu"] = (sofr + t["spread_usd"]) * p["tlu"]
        y["int_tle"] = (eur + t["spread_eur"]) * p["tle"]
        y["int_ssn"] = t["ssn_rate"] * p["ssn"]
        y["int_pik"] = (t["pik_pik_rate"] if tog == 1 else t["pik_cash_rate"]) * p["pik"]
        y["pik_accrued"] = y["int_pik"] * tog
        y["int_rcf"] = (sofr + j["rcf_spread"]) * p["rcf"] + j["commitment_fee"] * (t["rcf_capacity"] - p["rcf"])
        y["int_existing"] = j["existing_debt_rate"] * p["existing"]
        y["interest_total"] = y["int_tlu"] + y["int_tle"] + y["int_ssn"] + y["int_pik"] + y["int_rcf"] + y["int_existing"]
        y["cash_interest"] = y["interest_total"] - y["pik_accrued"]
        y["taxes"] = max(0.0, y["ebit"] - y["interest_total"]) * j["tax_rate"]
        y["ni_total"] = y["ebit"] - y["interest_total"] - y["taxes"]
        y["nci_dist"] = j["nci_pct"] * max(0.0, y["ni_total"])
        y["lfcf"] = y["ebitda"] - y["capex"] + y["change_nwc"] - y["taxes"] - y["cash_interest"] - y["nci_dist"]
        y["amort_u"] = min(j["tl_amort"] * t["tl_usd"], p["tlu"])
        y["amort_e"] = min(j["tl_amort"] * tr["tl_eur"], p["tle"])
        y["cash_pre"] = p["cash"] + y["lfcf"] - y["amort_u"] - y["amort_e"]
        y["rcf_draw"] = min(max(j["min_cash"] - y["cash_pre"], -p["rcf"]), t["rcf_capacity"] - p["rcf"])
        y["excess"] = max(0.0, y["cash_pre"] + y["rcf_draw"] - j["min_cash"])
        tl_after = p["tlu"] - y["amort_u"] + p["tle"] - y["amort_e"]
        y["sweep"] = min(y["excess"] * j["sweep_pct"], tl_after)
        y["sweep_u"] = y["sweep"] * (p["tlu"] - y["amort_u"]) / tl_after if tl_after > 0 else 0.0
        y["sweep_e"] = y["sweep"] - y["sweep_u"]
        y["tlu"] = p["tlu"] - y["amort_u"] - y["sweep_u"]
        y["tle"] = p["tle"] - y["amort_e"] - y["sweep_e"]
        y["ssn"] = p["ssn"]
        y["pik"] = p["pik"] + y["pik_accrued"]
        y["rcf"] = p["rcf"] + y["rcf_draw"]
        y["existing"] = p["existing"]
        y["cash"] = y["cash_pre"] + y["rcf_draw"] - y["sweep"]
        y["total_debt"] = y["tlu"] + y["tle"] + y["ssn"] + y["pik"] + y["rcf"] + y["existing"]
        y["net_debt"] = y["total_debt"] - y["cash"]
        y["nci_claim"] = tr["nci0"] * y["ebitda"] / tr["ebitda0"]
        y["lev_1l"] = (y["tlu"] + y["tle"] + y["ssn"] + y["rcf"] - y["cash"]) / y["ebitda"]
        y["lev_total"] = y["net_debt"] / y["ebitda"]
        y["icr"] = y["ebitda"] / y["cash_interest"]
        y["headroom"] = j["covenant_max_1l"] - y["lev_1l"]
        y["exit_ev"] = y["ebitda"] * tr["entry_mult"]
        y["exit_equity"] = y["exit_ev"] - y["net_debt"] - y["nci_claim"]
        y["investor_equity"] = y["exit_equity"] * (1 - j["mip_pct"])
        for key in out:
            out[key].append(y[key])
        p = y
    xy = int(j["exit_year"])
    i = xy - 1
    r = {**tr, **out}
    r["exit_mult"] = tr["entry_mult"]
    r["moic"] = out["investor_equity"][i] / tr["E0"]
    flows = [-tr["E0"]] + [out["investor_equity"][i] if k == i else 0.0 for k in range(n)]
    r["irr"] = irr(flows)
    r["irr_closed"] = r["moic"] ** (1 / xy) - 1
    r["attr_ebitda"] = (out["ebitda"][i] - tr["ebitda0"]) * tr["entry_mult"]
    r["attr_multiple"] = (r["exit_mult"] - tr["entry_mult"]) * out["ebitda"][i]
    r["attr_delever"] = tr["claims0"] - (out["net_debt"][i] + out["nci_claim"][i])
    r["attr_mip"] = -j["mip_pct"] * out["exit_equity"][i]
    r["value_created"] = out["investor_equity"][i] - tr["E0"]

    shares = t["shares_common"] + t["shares_awards"]
    steps_p = [-6.0, -3.0, 0.0, 3.0, 6.0]
    steps_m = [-2.0, -1.0, 0.0, 1.0, 2.0]
    r["grid_prices"] = [t["price_per_share"] + s for s in steps_p]
    r["grid_mults"] = [tr["entry_mult"] + s for s in steps_m]
    nd_x, nci_x, eb_x = out["net_debt"][i], out["nci_claim"][i], out["ebitda"][i]
    r["grid_price_mult"] = [[((eb_x * mm - nd_x - nci_x) * (1 - j["mip_pct"]) / (tr["E0"] + (pp - t["price_per_share"]) * shares))
                             ** (1 / xy) - 1 for mm in r["grid_mults"]] for pp in r["grid_prices"]]
    r["grid_years"] = [3, 4, 5, 6, 7]
    r["grid_year_mult"] = [[((out["ebitda"][yy - 1] * mm - out["net_debt"][yy - 1] - out["nci_claim"][yy - 1]) * (1 - j["mip_pct"])
                             / tr["E0"]) ** (1 / yy) - 1 for mm in r["grid_mults"]] for yy in r["grid_years"]]
    return r
