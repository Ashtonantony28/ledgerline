"""Independent reference for workbook 02 (docs/models/dcf-comps.md)."""
from __future__ import annotations

from ..models.assumptions import Inputs
from ..models.valuation_inputs import ValInputs
from . import three_statement

GRID = (-2, -1, 0, 1, 2)  # steps either side of the base case


def quartile_inc(xs: list[float], q: int) -> float:
    """Excel QUARTILE / QUARTILE.INC (linear interpolation, inclusive)."""
    s = sorted(xs)
    pos = (len(s) - 1) * q / 4
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def median(xs: list[float]) -> float:
    return quartile_inc(xs, 2)


def comps(v: ValInputs) -> dict:
    rows = []
    for c in v.comps:
        mcap = c.price * c.shares_out
        ev = mcap + c.debt - c.cash + c.nci
        rows.append({"ticker": c.ticker, "mcap": mcap, "ev": ev, "ev_rev": ev / c.revenue, "ev_ebitda": ev / c.ebitda,
                     "pe": c.price / c.eps})
    out = {"rows": rows}
    for k in ("ev_rev", "ev_ebitda", "pe"):
        xs = [r[k] for r in rows]
        out[k] = {"median": median(xs), "mean": sum(xs) / len(xs), "high": max(xs), "low": min(xs),
                  "q1": quartile_inc(xs, 1), "q3": quartile_inc(xs, 3)}
    return out


def run(inp: Inputs, v: ValInputs) -> dict:
    ts = three_statement.run(inp)
    o = three_statement.opening(inp)
    n = inp.n_fcst
    tax = inp.live("tax_rate")
    r: dict = {}
    beta_adj = v.blume_w * v.beta_raw + (1 - v.blume_w) * 1.0
    ke = v.rf + beta_adj * v.erp
    kd = (v.rf + v.credit_spread) * (1 - v.marginal_tax)
    mcap = v.price * v.shares_out
    debt0 = o["debt"]
    wd = debt0 / (debt0 + mcap)
    wacc = ke * (1 - wd) + kd * wd + v.wacc_shift
    r.update(beta_adj=beta_adj, ke=ke, kd_after_tax=kd, mcap=mcap, wd=wd, wacc=wacc)

    ebit, da, capex, dnwc = ts["operating_income"], ts["da"], ts["capex"], ts["change_nwc"]
    nopat = [e * (1 - t) for e, t in zip(ebit, tax)]
    ufcf = [np_ + d - c + w for np_, d, c, w in zip(nopat, da, capex, dnwc)]
    period = [k + 1 - v.midyear_adj for k in range(n)]
    df = [1 / (1 + wacc) ** p for p in period]
    pv = [u * f for u, f in zip(ufcf, df)]
    r.update(nopat=nopat, ufcf=ufcf, period=period, discount_factor=df, pv_ufcf=pv, sum_pv=sum(pv))

    cs = comps(v)
    r["comps"] = cs
    exit_mult = cs["ev_ebitda"]["median"]
    g = v.terminal_growth + v.growth_shift
    net_debt = debt0 - o["cash"] - o["st_investments"] + o["nci_equity"]
    roll = (1 + ke) ** v.years_since_fye

    def price_gordon(w: float, gg: float) -> float:
        dfw = [1 / (1 + w) ** p for p in period]
        ev = sum(u * f for u, f in zip(ufcf, dfw)) + ufcf[-1] * (1 + gg) / (w - gg) * dfw[-1]
        return (ev - net_debt) / v.shares_out * roll

    def price_exit(w: float, mult: float) -> float:
        dfw = [1 / (1 + w) ** p for p in period]
        ev = sum(u * f for u, f in zip(ufcf, dfw)) + ts["ebitda"][-1] * mult / (1 + w) ** n
        return (ev - net_debt) / v.shares_out * roll

    tv_g = ufcf[-1] * (1 + g) / (wacc - g)
    pv_tv_g = tv_g * df[-1]
    tv_x = ts["ebitda"][-1] * exit_mult
    pv_tv_x = tv_x / (1 + wacc) ** n
    ev_g, ev_x = sum(pv) + pv_tv_g, sum(pv) + pv_tv_x
    r.update(exit_multiple=exit_mult, net_debt=net_debt, roll_forward=roll,
             tv_gordon=tv_g, pv_tv_gordon=pv_tv_g, ev_gordon=ev_g, tv_share_gordon=pv_tv_g / ev_g,
             price_gordon=(ev_g - net_debt) / v.shares_out * roll,
             tv_exit=tv_x, pv_tv_exit=pv_tv_x, ev_exit=ev_x, tv_share_exit=pv_tv_x / ev_x,
             price_exit=(ev_x - net_debt) / v.shares_out * roll,
             implied_exit_multiple=tv_g / ts["ebitda"][-1],
             implied_growth_from_exit=(tv_x * wacc - ufcf[-1]) / (tv_x + ufcf[-1]))
    # Reverse DCF: perpetual growth the market price implies (Gordon, same WACC).
    ev_mkt = v.price / roll * v.shares_out + net_debt
    tv_needed = (ev_mkt - sum(pv)) / df[-1]
    r["market_ev"] = ev_mkt
    r["implied_growth_market"] = (tv_needed * wacc - ufcf[-1]) / (tv_needed + ufcf[-1])
    r["upside_gordon"] = r["price_gordon"] / v.price - 1
    r["upside_exit"] = r["price_exit"] / v.price - 1

    waccs = [wacc + k * v.wacc_step for k in GRID]
    r["grid_waccs"] = waccs
    r["grid_growths"] = [g + k * v.growth_step for k in GRID]
    r["grid_multiples"] = [exit_mult + k * v.multiple_step for k in GRID]
    r["grid_gordon"] = [[price_gordon(w, gg) for w in waccs] for gg in r["grid_growths"]]
    r["grid_exit"] = [[price_exit(w, mm) for w in waccs] for mm in r["grid_multiples"]]

    ebitda0 = ts_ebitda0 = inp.h("operating_income")[-1] + inp.h("da")[-1]
    eps0 = inp.h("net_income")[-1] / inp.h("shares_diluted")[-1]
    inner = lambda grid: [x for row in grid[1:4] for x in row[1:4]]
    r["football"] = {
        "dcf_gordon": (min(inner(r["grid_gordon"])), max(inner(r["grid_gordon"]))),
        "dcf_exit": (min(inner(r["grid_exit"])), max(inner(r["grid_exit"]))),
        "comps_ev_ebitda": tuple((cs["ev_ebitda"][q] * ebitda0 - net_debt) / v.shares_out for q in ("q1", "q3")),
        "comps_pe": tuple(cs["pe"][q] * eps0 for q in ("q1", "q3")),
        "range_52w": (v.lo_52w, v.hi_52w),
    }
    r["ebitda0"], r["eps0"] = ts_ebitda0, eps0
    return r
