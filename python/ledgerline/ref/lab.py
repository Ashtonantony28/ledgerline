"""Reference for workbook 07: tornado, spider, stress cases and Monte Carlo on the Costco DCF (docs/models/lab.md).

Every number is a full re-run of the three-statement and DCF references with additive shifts, so the lab's results
are exactly what the workbook would show with the same shifts typed into its Lab sheet (tests prove it for the
stress cases and a manual shift).
"""
from __future__ import annotations

import math
import random
from dataclasses import replace
from pathlib import Path

import yaml

from ..models.assumptions import Inputs
from ..models.valuation_inputs import ValInputs
from . import dcf

REPO = Path(__file__).resolve().parents[3]
VALUATION_KEYS = ("wacc", "terminal_growth")


def spec(ticker: str = "COST") -> dict:
    return yaml.safe_load((REPO / "spec" / f"LAB_{ticker}.yaml").read_text())


def price(inp: Inputs, v: ValInputs, shifts: dict[str, float]) -> tuple[float, float]:
    """(Gordon price, exit-multiple price) with additive shifts applied."""
    flex = {k: x for k, x in shifts.items() if k not in VALUATION_KEYS}
    i2 = replace(inp, flex=flex)
    v2 = replace(v, wacc_shift=shifts.get("wacc", 0.0), growth_shift=shifts.get("terminal_growth", 0.0))
    r = dcf.run(i2, v2)
    return r["price_gordon"], r["price_exit"]


def percentile(xs: list[float], p: float) -> float:
    """Excel PERCENTILE (inclusive, linear interpolation)."""
    s = sorted(xs)
    pos = p * (len(s) - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def montecarlo(inp: Inputs, v: ValInputs, sp: dict) -> dict:
    mc, drv = sp["monte_carlo"], sp["drivers"]
    rng = random.Random(mc["seed"])
    keys = list(drv)
    corr = {(a, b): rho for a, b, rho in mc.get("correlation", [])}
    base_spread = dcf.run(inp, v)["wacc"] - v.terminal_growth
    out_g, out_x, draws = [], [], []
    while len(out_g) < mc["trials"]:
        z = {k: rng.gauss(0.0, 1.0) for k in keys}
        for (a, b), rho in corr.items():  # b correlated with a
            z[b] = rho * z[a] + math.sqrt(1 - rho * rho) * z[b]
        sh = {k: z[k] * drv[k]["step"] for k in keys}
        if base_spread + sh["wacc"] - sh["terminal_growth"] < mc["min_spread"]:
            continue
        g, x = price(inp, v, sh)
        out_g.append(g)
        out_x.append(x)
        draws.append(sh)
    return {"gordon": out_g, "exit": out_x, "draws": draws}


def summary(xs: list[float], market: float, bins: int) -> dict:
    lo, hi = min(xs), max(xs)
    width = (hi - lo) / bins
    edges = [lo + k * width for k in range(bins + 1)]
    counts = [0] * bins
    for x in xs:
        counts[min(int((x - lo) / width), bins - 1)] += 1
    return {"mean": sum(xs) / len(xs), "p": {q: percentile(xs, q) for q in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)},
            "prob_above_market": sum(1 for x in xs if x > market) / len(xs), "edges": edges, "counts": counts}


def run(inp: Inputs, v: ValInputs, ticker: str = "COST", trials: int | None = None) -> dict:
    sp = spec(ticker)
    if trials:
        sp["monte_carlo"]["trials"] = trials
    drv = sp["drivers"]
    base = price(inp, v, {})
    r = {"base": base, "market": v.price}
    tor = []
    for k, d in drv.items():
        lo, hi = price(inp, v, {k: -d["step"]}), price(inp, v, {k: d["step"]})
        tor.append({"key": k, "label": d["label"], "step": d["step"], "low": lo, "high": hi,
                    "swing": abs(hi[0] - lo[0])})
    r["tornado"] = sorted(tor, key=lambda t: -t["swing"])
    r["spider"] = {k: [price(inp, v, {k: s * d["step"]}) for s in sp["spider_steps"]] for k, d in drv.items()}
    r["stress"] = [{"name": s["name"], "shifts": s["shifts"], "price": price(inp, v, s["shifts"])} for s in sp["stress"]]
    mc = montecarlo(inp, v, sp)
    r["mc"] = {"gordon": summary(mc["gordon"], v.price, sp["monte_carlo"]["bins"]),
               "exit": summary(mc["exit"], v.price, sp["monte_carlo"]["bins"]),
               "trials": len(mc["gordon"]), "seed": sp["monte_carlo"]["seed"]}
    r["spec"] = sp
    return r
