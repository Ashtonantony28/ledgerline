"""Reference for workbook 09: credit spreads, Altman Z', rating scorecard, covenants, debt capacity, stress
(docs/models/credit.md). One column per borrower, latest fiscal year in its fixture.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from ..data.history import load

REPO = Path(__file__).resolve().parents[3]
M = 1e6
# spread item -> fixture keys summed (all in $m)
ITEMS = {
    "revenue": ["revenue"], "operating_income": ["operating_income"], "da": ["da"],
    "interest_expense": ["interest_expense"], "interest_nonop_net": ["interest_nonop_net"],
    "debt": ["current_debt", "lt_debt", "short_term_debt"], "leases": ["op_lease_liab_current", "op_lease_liab_noncurrent"],
    "cash": ["cash"], "st_investments": ["st_investments"], "total_assets": ["total_assets"],
    "total_liabilities": ["total_liabilities"], "current_assets": ["total_current_assets"],
    "current_liabilities": ["total_current_liabilities"], "retained_earnings": ["retained_earnings"],
    "total_equity": ["total_equity"], "temp_equity": ["temp_equity"], "cfo": ["cfo"], "capex": ["capex"],
    "net_income": ["net_income"],
}


@dataclass
class Borrower:
    ticker: str
    entity: str
    fy_end: date
    v: dict[str, float]
    src: dict[str, str]


def spec() -> dict:
    return yaml.safe_load((REPO / "spec" / "CREDIT.yaml").read_text())


def borrowers(sp: dict | None = None) -> list[Borrower]:
    sp = sp or spec()
    out = []
    for t in sp["borrowers"]:
        h = load(t)
        i = len(h.period_ends) - 1
        v = {k: sum(h.values[x][i] for x in keys) / M for k, keys in ITEMS.items()}
        src = {k: "; ".join(f"{x}: {h.source[x][i]}" for x in keys) for k, keys in ITEMS.items()}
        out.append(Borrower(t, h.entity, h.period_ends[i], v, src))
    return out


def round_half_up(x: float) -> int:
    """Excel ROUND(x, 0) for positive x."""
    return math.floor(x + 0.5)


def band_leverage(x: float, bounds: list[float]) -> int:
    return 1 + sum(1 for b in bounds if b < x)


def band_coverage(x: float, bounds: list[float]) -> int:
    return 1 + sum(1 for b in bounds if b > x)


def score(lev: float, cov: float, z: float, sp: dict) -> int:
    sc, al = sp["scorecard"], sp["altman"]
    w = sc["leverage_weight"]
    base = round_half_up(w * band_leverage(lev, sc["leverage_bounds"]) + (1 - w) * band_coverage(cov, sc["coverage_bounds"]))
    return min(len(sc["ratings"]), base + (sc["distress_notches"] if z < al["distress"] else 0))


def zscore(v: dict, ebit: float, sp: dict) -> float:
    c = sp["altman"]["coef"]
    ta = v["total_assets"]
    return (c["wc_ta"] * (v["current_assets"] - v["current_liabilities"]) / ta + c["re_ta"] * v["retained_earnings"] / ta
            + c["ebit_ta"] * ebit / ta + c["eq_tl"] * v["total_equity"] / v["total_liabilities"] + c["sales_ta"] * v["revenue"] / ta)


def analyse(b: Borrower, sp: dict) -> dict:
    v, sc, cv, cap, st = b.v, sp["scorecard"], sp["covenants"], sp["capacity"], sp["stress"]
    r: dict = {"ticker": b.ticker, "fy_end": b.fy_end.isoformat()}
    r["ebitda"] = v["operating_income"] + v["da"]
    r["interest"] = v["interest_expense"] if v["interest_expense"] > 0 else v["interest_nonop_net"]
    r["adj_debt"] = v["debt"] + v["leases"]
    r["net_debt"] = r["adj_debt"] - v["cash"] - v["st_investments"]
    r["leverage"] = r["adj_debt"] / r["ebitda"]
    r["net_leverage"] = r["net_debt"] / r["ebitda"]
    r["coverage"] = r["ebitda"] / r["interest"]
    r["ebit_coverage"] = v["operating_income"] / r["interest"]
    r["fcf"] = v["cfo"] + v["capex"]
    r["fcf_debt"] = r["fcf"] / r["adj_debt"]
    r["cfo_debt"] = v["cfo"] / r["adj_debt"]
    r["z"] = zscore(v, v["operating_income"], sp)
    r["zone"] = "Distress" if r["z"] < sp["altman"]["distress"] else ("Grey" if r["z"] < sp["altman"]["safe"] else "Safe")
    r["lev_band"] = band_leverage(r["leverage"], sc["leverage_bounds"])
    r["cov_band"] = band_coverage(r["coverage"], sc["coverage_bounds"])
    r["idx"] = score(r["leverage"], r["coverage"], r["z"], sp)
    r["rating"], r["pd"] = sc["ratings"][r["idx"] - 1], sc["pd_1y"][r["idx"] - 1]
    r["lev_cushion"] = 1 - r["adj_debt"] / (cv["max_leverage"] * r["ebitda"])
    r["cov_cushion"] = 1 - cv["min_coverage"] * r["interest"] / r["ebitda"]
    r["cushion"] = min(r["lev_cushion"], r["cov_cushion"])
    r["cap_leverage"] = cap["target_leverage"] * r["ebitda"] - r["adj_debt"]
    r["cap_coverage"] = (r["ebitda"] / cap["min_coverage"] - r["interest"]) / cap["marginal_rate"]
    r["capacity"] = min(r["cap_leverage"], r["cap_coverage"])
    # stress
    r["s_ebitda"] = r["ebitda"] * (1 - st["ebitda_shock"])
    r["s_interest"] = r["interest"] + st["rate_shock"] * st["floating_share"] * v["debt"]
    r["s_leverage"] = r["adj_debt"] / r["s_ebitda"]
    r["s_coverage"] = r["s_ebitda"] / r["s_interest"]
    r["s_z"] = zscore(v, v["operating_income"] - st["ebitda_shock"] * r["ebitda"], sp)
    r["s_idx"] = score(r["s_leverage"], r["s_coverage"], r["s_z"], sp)
    r["s_rating"], r["s_pd"] = sc["ratings"][r["s_idx"] - 1], sc["pd_1y"][r["s_idx"] - 1]
    r["s_breach"] = 1 if (r["s_leverage"] > cv["max_leverage"] or r["s_coverage"] < cv["min_coverage"]) else 0
    r["notches"] = r["s_idx"] - r["idx"]
    r["bs_tie"] = v["total_assets"] - v["total_liabilities"] - v["total_equity"] - v["temp_equity"]
    return r


def run(sp: dict | None = None) -> dict:
    sp = sp or spec()
    bs = borrowers(sp)
    return {"borrowers": bs, "results": [analyse(b, sp) for b in bs], "spec": sp}
