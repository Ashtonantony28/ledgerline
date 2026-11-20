"""Independent reference for workbook 04, M&A accretion/dilution (docs/models/mna.md)."""
from __future__ import annotations

from ..models.mna_inputs import MnAInputs


def amort(step: float, life: float, k: int) -> float:
    """Straight-line charge in year k (1-based) of `step` over `life` years, stopping once fully amortised."""
    return max(0.0, min(step / life, step - step / life * (k - 1)))


def financing(inp: MnAInputs, price: float, pct: float) -> dict:
    """Cash uses, new notes and balance-sheet cash for an offer price and stock share (ADR 0005: closed form)."""
    t, j = inp.tx, inp.j
    n = t["fl_shares"] - t["dks_held_fl"]
    r = {"n": n, "new_shares": n * pct * t["exchange_ratio"] * price / t["offer_price"]}
    r["cash_holders"] = n * (1 - pct) * price
    r["cash_uses"] = r["cash_holders"] + t["awards_cash"] + t["txn_costs"] + t["severance"] + t["retention"] + t["seller_costs"]
    r["avail"] = inp.ha("cash")[-1] + inp.ht("cash")[-1] - j["min_cash"]
    r["new_debt"] = max(0.0, (r["cash_uses"] - r["avail"]) / (1 - t["issuance_fee"]))
    r["issuance_cost"] = r["new_debt"] * t["issuance_fee"]
    r["cash_used"] = r["cash_uses"] + r["issuance_cost"] - r["new_debt"]
    return r


def transaction(inp: MnAInputs) -> dict:
    t, j = inp.tx, inp.j
    p, P = inp.pct_stock(), inp.dks_price()
    r = financing(inp, t["offer_price"], p)
    r["stock_value"] = r["new_shares"] * P
    r["per_share_value"] = p * t["exchange_ratio"] * P + (1 - p) * t["offer_price"]
    r["stake_fv"] = t["dks_held_fl"] * r["per_share_value"]
    r["consideration"] = r["cash_holders"] + t["awards_cash"] + r["stock_value"] + r["stake_fv"] + t["replaced_awards"]
    r["stake_gain"] = r["stake_fv"] - t["stake_carrying"]
    r["uses"] = r["cash_uses"] + r["issuance_cost"]
    r["sources"] = r["new_debt"] + r["cash_used"]
    r["cash_close"] = inp.ha("cash")[-1] + inp.ht("cash")[-1] - r["cash_used"]
    # Purchase price allocation
    eq, gw, ia = inp.ht("parent_equity")[-1], inp.ht("goodwill")[-1], inp.ht("intangibles")[-1]
    r["tangible_book"] = eq - gw - ia
    r["dtl"] = t["pf_tax_rate"] * (t["ppe_stepup"] + t["intangibles_fv"] - ia + t["lease_favourable"] + t["notes_fv_adj"])
    r["net_assets"] = (r["tangible_book"] + t["intangibles_fv"] + t["ppe_stepup"] + t["lease_favourable"] + t["notes_fv_adj"]
                       - r["dtl"] - t["seller_costs"])
    r["excess"] = r["consideration"] - r["net_assets"]
    r["goodwill"] = max(0.0, r["excess"])
    r["bargain_gain"] = max(0.0, -r["excess"])
    # Valuation and credit at close
    r["offer_equity"] = t["fl_shares"] * t["offer_price"]
    fl_debt = inp.ht("current_debt")[-1] + inp.ht("lt_debt")[-1]
    r["offer_ev"] = r["offer_equity"] + fl_debt - inp.ht("cash")[-1]
    r["ev_ebitda_ltm"] = r["offer_ev"] / (inp.ht("operating_income")[-1] + inp.ht("da")[-1])
    r["pf_debt"] = inp.ha("current_debt")[-1] + inp.ha("lt_debt")[-1] + fl_debt - t["notes_fv_adj"] + r["new_debt"]
    r["pf_net_debt"] = r["pf_debt"] - r["cash_close"]
    return r


def run(inp: MnAInputs) -> dict:
    t, j = inp.tx, inp.j
    tr = transaction(inp)
    n = inp.n_fcst
    tax = t["pf_tax_rate"]
    proj = inp.fl_proj[inp.case]
    keys = ("dks_revenue", "dks_ebitda", "dks_da", "dks_ebit", "dks_interest", "dks_int_income", "dks_pretax", "dks_tax",
            "dks_ni", "eps_sa", "fl_revenue", "fl_ebitda", "fl_da", "fl_pretax", "fl_tax", "fl_ni", "syn", "dep_step",
            "amort_int", "lease_amort", "notes_accr", "fl_amort_elim", "new_int", "iss_amort", "lost_int", "adj_pretax",
            "pf_ni_adj", "close_items", "integration", "pf_ni_gaap", "pf_shares", "eps_adj", "eps_gaap", "acc_adj",
            "acc_gaap", "breakeven_syn", "breakeven_fl_ni", "pf_ebitda", "pf_leverage", "pf_ni_pre_fin")
    out: dict = {k: [] for k in keys}
    rev = inp.ha("revenue")[-1]
    shares = inp.ha("shares_diluted")[-1]
    for k in range(n):
        y = {}
        rev = rev * (1 + inp.live("dks_revenue_growth")[k])
        y["dks_revenue"] = rev
        y["dks_ebitda"] = rev * inp.live("dks_ebitda_margin")[k]
        y["dks_da"] = rev * inp.live("dks_da_pct")[k]
        y["dks_ebit"] = y["dks_ebitda"] - y["dks_da"]
        y["dks_interest"] = inp.ha("interest_expense")[-1]
        y["dks_int_income"] = inp.ha("cash")[-1] * j["cash_yield"]
        y["dks_pretax"] = y["dks_ebit"] - y["dks_interest"] + y["dks_int_income"]
        y["dks_tax"] = y["dks_pretax"] * j["dks_tax_rate"]
        y["dks_ni"] = y["dks_pretax"] - y["dks_tax"]
        y["eps_sa"] = y["dks_ni"] / shares
        y["fl_revenue"] = proj["revenue"][k]
        y["fl_ebitda"] = proj["ebitda"][k]
        y["fl_da"] = y["fl_revenue"] * inp.live("fl_da_pct")[k]
        y["fl_pretax"] = y["fl_ebitda"] - y["fl_da"] - inp.ht("interest_expense")[-1]
        y["fl_tax"] = y["fl_pretax"] * j["fl_tax_rate"]
        y["fl_ni"] = y["fl_pretax"] - y["fl_tax"]
        yr = k + 1
        y["syn"] = inp.syn_runrate[inp.case] * inp.syn_phase[k]
        y["dep_step"] = amort(t["ppe_stepup"], j["ppe_life"], yr)
        y["amort_int"] = amort(t["finite_intangibles"], j["finite_life"], yr)
        y["lease_amort"] = amort(t["lease_favourable"], j["lease_life"], yr)
        y["notes_accr"] = amort(t["notes_fv_adj"], j["notes_life"], yr)
        y["fl_amort_elim"] = t["fl_hist_amort"]
        y["new_int"] = tr["new_debt"] * t["notes_rate"]
        y["iss_amort"] = amort(tr["issuance_cost"], j["issuance_term"], yr) if tr["issuance_cost"] > 0 else 0.0
        y["lost_int"] = tr["cash_used"] * j["cash_yield"]
        y["adj_pretax"] = (y["syn"] - y["dep_step"] - y["amort_int"] - y["lease_amort"] - y["notes_accr"] + y["fl_amort_elim"]
                           - y["new_int"] - y["iss_amort"] - y["lost_int"])
        y["pf_ni_adj"] = y["dks_ni"] + y["fl_ni"] + y["adj_pretax"] * (1 - tax)
        y["close_items"] = (t["txn_costs"] + t["severance"] + t["retention"] - tr["stake_gain"] - tr["bargain_gain"]) if yr == 1 else 0.0
        y["integration"] = inp.syn_costs[k]
        y["pf_ni_gaap"] = y["pf_ni_adj"] - (y["close_items"] + y["integration"]) * (1 - tax)
        y["pf_shares"] = shares + tr["new_shares"]
        y["eps_adj"] = y["pf_ni_adj"] / y["pf_shares"]
        y["eps_gaap"] = y["pf_ni_gaap"] / y["pf_shares"]
        y["acc_adj"] = y["eps_adj"] / y["eps_sa"] - 1
        y["acc_gaap"] = y["eps_gaap"] / y["eps_sa"] - 1
        y["breakeven_syn"] = y["syn"] - (y["pf_ni_adj"] - y["eps_sa"] * y["pf_shares"]) / (1 - tax)
        y["breakeven_fl_ni"] = y["fl_ni"] - (y["pf_ni_adj"] - y["eps_sa"] * y["pf_shares"])
        y["pf_ebitda"] = y["dks_ebitda"] + y["fl_ebitda"] + y["syn"]
        y["pf_leverage"] = tr["pf_net_debt"] / y["pf_ebitda"]
        y["pf_ni_pre_fin"] = y["pf_ni_adj"] + (y["new_int"] + y["iss_amort"] + y["lost_int"]) * (1 - tax)
        for key in out:
            out[key].append(y[key])
    r = {**tr, **out}
    r["dks_shares"] = shares
    r["ev_ebitda_fwd"] = tr["offer_ev"] / out["fl_ebitda"][0]
    # Contribution analysis, first forecast year
    r["contrib_rev"] = out["dks_revenue"][0] / (out["dks_revenue"][0] + out["fl_revenue"][0])
    r["contrib_ebitda"] = out["dks_ebitda"][0] / (out["dks_ebitda"][0] + out["fl_ebitda"][0])
    r["contrib_ni"] = out["dks_ni"][0] / (out["dks_ni"][0] + out["fl_ni"][0])
    r["own_dks"] = shares / out["pf_shares"][0]
    r["own_fl"] = tr["new_shares"] / out["pf_shares"][0]
    r["sa_leverage"] = (inp.ha("current_debt")[-1] + inp.ha("lt_debt")[-1] - inp.ha("cash")[-1]) / out["dks_ebitda"][0]

    # Sensitivities (closed form, see spec)
    step_p, step_s = 2.0, 0.25
    k2 = int(j["acc_year"]) - 1  # FY2026: first full fiscal year after the September 2025 close
    r["grid_prices"] = [t["offer_price"] + step_p * d for d in (-2, -1, 0, 1, 2)]
    r["grid_pcts"] = [step_s * d for d in range(5)]

    def acc(price, pct):
        f = financing(inp, price, pct)
        fin = f["new_debt"] * t["notes_rate"] + (f["issuance_cost"] / j["issuance_term"]) + f["cash_used"] * j["cash_yield"]
        ni = out["pf_ni_pre_fin"][k2] - fin * (1 - tax)
        return ni / (shares + f["new_shares"]) / out["eps_sa"][k2] - 1

    r["grid_price_pct"] = [[acc(pp, ss) for ss in r["grid_pcts"]] for pp in r["grid_prices"]]
    r["grid_syn"] = [0.0, 0.5, 1.0, 1.5]
    r["grid_year_syn"] = [[(out["pf_ni_adj"][k] + (f - 1) * out["syn"][k] * (1 - tax)) / out["pf_shares"][k] / out["eps_sa"][k] - 1
                           for f in r["grid_syn"]] for k in range(n)]
    return r
