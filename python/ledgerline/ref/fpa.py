"""Independent reference for workbook 06, FP&A budget and rolling forecast (docs/models/fpa.md).

All series run over the full timeline: n_actual months of actuals then n_forecast months of rolling forecast.
"""
from __future__ import annotations

PRODUCTS = ["Core", "Premium", "Services"]
DEPTS = ["SalesMarketing", "Operations", "GA"]
CASES = ["base", "upside", "downside"]


def run(g: dict, scenario: int = 1) -> dict:
    s, act = g["spec"], g["act"]
    cal, py, b, fc, fin = s["calendar"], s["prior_year"], s["budget"], s["forecast"], s["finance"]
    nh, nf, nb, lb = cal["n_actual"], cal["n_forecast"], cal["budget_months"], cal["lookback"]
    T, Y = nh + nf, 12
    case = fc["scenarios"][CASES[scenario - 1]]
    r: dict = {}

    # calendar
    month_idx = [(t % Y) + 1 for t in range(T)]
    in_budget = [1.0 if t < nb else 0.0 for t in range(T)]
    seas = [b["seasonality"][mi - 1] for mi in month_idx]
    r["seas_sum"] = sum(b["seasonality"])

    # ---------------------------------------------------------------- budget
    for p in PRODUCTS:
        pr = s["products"][p]
        vol_py = pr["share"] * py["revenue"] / pr["price"]
        bv = [vol_py * (1 + b["volume_growth"][p]) * seas[t] * in_budget[t] for t in range(T)]
        bpx = [pr["price"] * (1 + b["price_increase"][p]) * in_budget[t] for t in range(T)]
        buc = [pr["unit_cost"] * (1 + b["cost_inflation"][p]) * in_budget[t] for t in range(T)]
        r[f"bvol_{p}"], r[f"bprice_{p}"] = bv, bpx
        r[f"brev_{p}"] = [bv[t] * bpx[t] for t in range(T)]
        r[f"bcogs_{p}"] = [bv[t] * buc[t] for t in range(T)]
        r[f"pyvol_{p}"] = vol_py
    r["brev"] = [sum(r[f"brev_{p}"][t] for p in PRODUCTS) for t in range(T)]
    r["bcogs"] = [sum(r[f"bcogs_{p}"][t] for p in PRODUCTS) for t in range(T)]
    r["bgp"] = [r["brev"][t] - r["bcogs"][t] for t in range(T)]
    for d in DEPTS:
        dd = b["departments"][d]
        hires = dd["hires"] + [0] * (T - len(dd["hires"]))
        heads = [dd["heads_open"] + sum(hires[: t + 1]) for t in range(T)]
        r[f"bheads_{d}"] = heads
        r[f"bpeople_{d}"] = [heads[t] * dd["cost_per_head"] * (1 + b["pay_raise"]) / Y * in_budget[t] for t in range(T)]
    r["bnp_SalesMarketing"] = [b["sm_nonpeople_pct"] * r["brev"][t] for t in range(T)]
    r["bnp_Operations"] = [b["ops_nonpeople"] / Y * in_budget[t] for t in range(T)]
    r["bnp_GA"] = [b["ga_nonpeople"] / Y * in_budget[t] for t in range(T)]
    for d in DEPTS:
        r[f"bopex_{d}"] = [r[f"bpeople_{d}"][t] + r[f"bnp_{d}"][t] for t in range(T)]
    r["bopex"] = [sum(r[f"bopex_{d}"][t] for d in DEPTS) for t in range(T)]
    r["bebitda"] = [r["bgp"][t] - r["bopex"][t] for t in range(T)]

    # ---------------------------------------------------------------- live drivers: actuals, then forecast
    A = lambda acct, dim: act[(acct, dim)]
    win = range(nh - lb, nh)
    for p in PRODUCTS:
        av, ar, ac = A("volume", p), A("revenue", p), A("cogs", p)
        rr = sum(av[t] for t in win) / sum(seas[t] for t in win)
        r[f"rr_{p}"] = rr
        g_, px_ = case["growth"][p], case["price"][p]
        vol, price, uc, gi = list(av), [ar[t] / av[t] for t in range(nh)], [ac[t] / av[t] for t in range(nh)], [1.0] * nh
        for t in range(nh, T):
            gi.append(gi[-1] * (1 + g_))
            vol.append(rr * seas[t] * gi[t])
            price.append(price[-1] * (1 + px_))
            uc.append(uc[-1] * (1 + fc["cost_inflation_month"][p]))
        r[f"vol_{p}"], r[f"price_{p}"], r[f"uc_{p}"] = vol, price, uc
        r[f"rev_{p}"] = [vol[t] * price[t] for t in range(T)]
        r[f"cogs_{p}"] = [vol[t] * uc[t] for t in range(T)]
    r["rev"] = [sum(r[f"rev_{p}"][t] for p in PRODUCTS) for t in range(T)]
    r["cogs"] = [sum(r[f"cogs_{p}"][t] for p in PRODUCTS) for t in range(T)]
    r["gp"] = [r["rev"][t] - r["cogs"][t] for t in range(T)]
    for d in DEPTS:
        ah, ap, an = A("heads", d), A("people_cost", d), A("nonpeople_cost", d)
        heads, cph = list(ah), [ap[t] / ah[t] for t in range(nh)]
        for t in range(nh, T):
            heads.append(heads[-1] + case["hires"][d])
            cph.append(cph[-1] * (1 + fc["wage_inflation_month"]))
        r[f"heads_{d}"], r[f"cph_{d}"] = heads, cph
        r[f"people_{d}"] = [heads[t] * cph[t] for t in range(T)]
        if d == "SalesMarketing":
            pct = sum(an[t] for t in win) / sum(r["rev"][t] for t in win)
            r["np_sm_pct"] = pct
            r[f"np_{d}"] = list(an) + [pct * r["rev"][t] for t in range(nh, T)]
        else:
            rr = sum(an[t] for t in win) / lb
            r[f"np_rr_{d}"] = rr
            r[f"np_{d}"] = list(an) + [rr] * nf
        r[f"opex_{d}"] = [r[f"people_{d}"][t] + r[f"np_{d}"][t] for t in range(T)]
    r["opex"] = [sum(r[f"opex_{d}"][t] for d in DEPTS) for t in range(T)]
    r["ebitda"] = [r["gp"][t] - r["opex"][t] for t in range(T)]
    capex = list(A("capex", "Group")) + [fc["capex_month"]] * nf
    r["capex"] = capex
    r["dep"] = [py["dep_annual"] / Y + sum(capex[: t + 1]) / fin["life_new_months"] for t in range(T)]
    r["ebit"] = [r["ebitda"][t] - r["dep"][t] for t in range(T)]
    r["tax"] = [fin["tax_rate"] * max(0.0, r["ebit"][t]) for t in range(T)]
    r["nwc"] = [s["prior_year"]["nwc"] / py["revenue"] * r["rev"][t] * Y for t in range(T)]
    prev = [py["nwc"]] + r["nwc"][:-1]
    r["dnwc"] = [r["nwc"][t] - prev[t] for t in range(T)]
    r["fcf"] = [r["ebitda"][t] - r["tax"][t] - r["dnwc"][t] - capex[t] for t in range(T)]
    cash, c = [], py["cash"]
    for t in range(T):
        c += r["fcf"][t]
        cash.append(c)
    r["cash"] = cash
    fcash = cash[nh:]
    r["min_cash_fc"] = min(fcash)
    r["min_cash_month"] = nh + fcash.index(min(fcash))
    r["headroom"] = r["min_cash_fc"] - fin["min_cash"]

    # ---------------------------------------------------------------- variance bridges (YTD = actual months; FY = budget year)
    for scope, rng_ in (("ytd", range(nh)), ("fy", range(nb))):
        S = lambda k: sum(r[k][t] for t in rng_)
        AV = {p: S(f"vol_{p}") for p in PRODUCTS}
        AR = {p: S(f"rev_{p}") for p in PRODUCTS}
        AC = {p: S(f"cogs_{p}") for p in PRODUCTS}
        BV = {p: S(f"bvol_{p}") for p in PRODUCTS}
        BR = {p: S(f"brev_{p}") for p in PRODUCTS}
        BC = {p: S(f"bcogs_{p}") for p in PRODUCTS}
        AVt, BVt, BRt, BCt = sum(AV.values()), sum(BV.values()), sum(BR.values()), sum(BC.values())
        BGP = BRt - BCt
        x = {}
        x["rev_actual"], x["rev_budget"] = sum(AR.values()), BRt
        x["price"] = sum(AR[p] - AV[p] * BR[p] / BV[p] for p in PRODUCTS)
        x["rev_volume"] = (AVt - BVt) * BRt / BVt
        x["rev_mix"] = sum(AV[p] * BR[p] / BV[p] for p in PRODUCTS) - AVt * BRt / BVt
        x["cost"] = -sum(AC[p] - AV[p] * BC[p] / BV[p] for p in PRODUCTS)
        x["gp_volume"] = (AVt - BVt) * BGP / BVt
        x["gp_mix"] = sum(AV[p] * (BR[p] - BC[p]) / BV[p] for p in PRODUCTS) - AVt * BGP / BVt
        heads_v = rate_v = np_v = 0.0
        for d in DEPTS:
            ahm, bhm = S(f"heads_{d}"), sum(r[f"bheads_{d}"][t] * in_budget[t] for t in rng_)
            bcph = S(f"bpeople_{d}") / bhm
            x[f"heads_{d}"] = (ahm - bhm) * bcph
            x[f"rate_{d}"] = S(f"people_{d}") - ahm * bcph
            x[f"np_{d}"] = S(f"np_{d}") - S(f"bnp_{d}")
            heads_v += x[f"heads_{d}"]
            rate_v += x[f"rate_{d}"]
            np_v += x[f"np_{d}"]
        x["heads"], x["rate"], x["np"] = heads_v, rate_v, np_v
        x["ebitda_budget"], x["ebitda_actual"] = S("bebitda"), S("ebitda")
        x["ebitda_bridge"] = (x["ebitda_budget"] + x["price"] + x["cost"] + x["gp_volume"] + x["gp_mix"]
                              - x["heads"] - x["rate"] - x["np"])
        x["opex_var"] = S("opex") - S("bopex")
        r[scope] = x

    # ---------------------------------------------------------------- forecast accuracy (forecast made at the June close)
    prior = g["prior"]
    r["prior"] = prior
    hist_months = [m for m in sorted(prior) if m <= nh]
    err = {m: prior[m] - r["rev"][m - 1] for m in hist_months}
    r["fc_err"] = err
    r["fc_ape"] = {m: abs(err[m]) / r["rev"][m - 1] for m in hist_months}
    r["mape"] = sum(r["fc_ape"].values()) / len(hist_months)
    r["bias"] = sum(err.values()) / sum(r["rev"][m - 1] for m in hist_months)
    fut = [m for m in sorted(prior) if m > nh]
    r["q4_change"] = sum(r["rev"][m - 1] for m in fut) - sum(prior[m] for m in fut)
    return r
