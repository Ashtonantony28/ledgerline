"""Seeded synthetic monthly actuals for workbook 06 (FP&A), written as a GL-style export.

    python -m ledgerline.data.fpa          # regenerate fixtures/fpa/ (a reviewed change)

The actuals start from the FY2026 budget in spec/FPA.yaml and drift the way a real year does, so the variance
bridges have something to explain: Core volume weakens from May, Core unit cost jumps in June (a tariff), Premium
realises a better price, Services runs ahead on volume, sales hiring lags plan by two months and G&A overspends
from April. Small seeded noise sits on top. Output is a long table (month, account, dimension, value), the shape
an ERP export has and the shape the workbook's Power Query script ingests.
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "spec" / "FPA.yaml"
OUT = REPO / "fixtures" / "fpa"
SEED = 2026
PRODUCTS = ["Core", "Premium", "Services"]
DEPTS = ["SalesMarketing", "Operations", "GA"]


def spec() -> dict:
    return yaml.safe_load(SPEC.read_text())


def budget_path(s: dict) -> dict:
    """Monthly budget volumes, prices, unit costs and heads, straight from the spec (used only to seed actuals)."""
    py, b = s["prior_year"], s["budget"]
    out = {}
    for p in PRODUCTS:
        pr = s["products"][p]
        vol_py = pr["share"] * py["revenue"] / pr["price"]
        out[p] = dict(vol=[vol_py * (1 + b["volume_growth"][p]) * w for w in b["seasonality"]],
                      price=pr["price"] * (1 + b["price_increase"][p]), uc=pr["unit_cost"] * (1 + b["cost_inflation"][p]))
    for d in DEPTS:
        dd = b["departments"][d]
        heads, h = [], dd["heads_open"]
        for x in dd["hires"]:
            h += x
            heads.append(h)
        out[d] = dict(heads=heads, cph=dd["cost_per_head"] * (1 + b["pay_raise"]))
    return out


def generate(s: dict | None = None) -> dict:
    s = s or spec()
    rng = random.Random(SEED)
    n = s["calendar"]["n_actual"]
    b, bp = s["budget"], budget_path(s)
    months = 12
    rows: list[tuple[int, str, str, float]] = []
    drift_vol = {"Core": lambda m: -0.06 if m >= 5 else -0.01, "Premium": lambda m: 0.0, "Services": lambda m: 0.07 if m >= 3 else 0.02}
    drift_px = {"Core": -0.010, "Premium": 0.025, "Services": 0.0}
    drift_uc = {"Core": lambda m: 0.05 if m >= 6 else 0.0, "Premium": lambda m: 0.0, "Services": lambda m: -0.01}
    act = {p: {"vol": [], "rev": []} for p in PRODUCTS}
    for m in range(1, n + 1):
        rev_total = 0.0
        for p in PRODUCTS:
            vol = round(bp[p]["vol"][m - 1] * (1 + drift_vol[p](m)) * (1 + rng.gauss(0, 0.02)), 4)
            price = bp[p]["price"] * (1 + drift_px[p]) * (1 + rng.gauss(0, 0.005))
            uc = bp[p]["uc"] * (1 + drift_uc[p](m)) * (1 + rng.gauss(0, 0.005))
            rev, cogs = round(vol * price, 3), round(vol * uc, 3)
            rows += [(m, "volume", p, vol), (m, "revenue", p, rev), (m, "cogs", p, cogs)]
            act[p]["vol"].append(vol)
            act[p]["rev"].append(rev)
            rev_total += rev
        opex_total = 0.0
        for d in DEPTS:
            lag = 2 if d == "SalesMarketing" else 0
            budget_heads = bp[d]["heads"]
            heads = budget_heads[max(m - 1 - lag, 0)] if m - 1 - lag >= 0 else b["departments"][d]["heads_open"]
            heads = int(round(heads + rng.gauss(0, 2)))
            people = round(heads * bp[d]["cph"] / months * (1 + rng.gauss(0, 0.004)), 3)
            if d == "SalesMarketing":
                np_ = rev_total * (b["sm_nonpeople_pct"] + 0.004) * (1 + rng.gauss(0, 0.03))
            elif d == "Operations":
                np_ = b["ops_nonpeople"] / months * (1 + rng.gauss(0, 0.03))
            else:
                np_ = b["ga_nonpeople"] / months * (1.08 if m >= 4 else 1.0) * (1 + rng.gauss(0, 0.03))
            np_ = round(np_, 3)
            rows += [(m, "heads", d, heads), (m, "people_cost", d, people), (m, "nonpeople_cost", d, np_)]
            opex_total += people + np_
        rows.append((m, "capex", "Group", round(b["capex_month"] * (1 + rng.gauss(0, 0.15)), 3)))
        # GL control totals (what the trial balance says; the sub-ledger detail above must tie to them)
        rows.append((m, "gl_revenue", "Group", round(rev_total, 3)))
        rows.append((m, "gl_opex", "Group", round(opex_total, 3)))
    # the forecast made at the June close (6+6): run-rate of Apr-Jun volumes, June price, held flat
    seas = b["seasonality"]
    prior = []
    for m in range(7, 13):
        tot = 0.0
        for p in PRODUCTS:
            rr = sum(act[p]["vol"][3:6]) / sum(seas[3:6])
            px = act[p]["rev"][5] / act[p]["vol"][5]
            tot += rr * seas[m - 1] * px
        prior.append((m, round(tot, 3)))
    return {"actuals": rows, "prior_forecast": prior}


def write(g: dict, out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "actuals.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["month", "account", "dimension", "value"])
        for m, a, d, v in g["actuals"]:
            w.writerow([m, a, d, v])
    with open(out / "prior_forecast.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["month", "revenue_forecast_at_jun"])
        for m, v in g["prior_forecast"]:
            w.writerow([m, v])


def load(base: Path = OUT) -> dict:
    """{'act': {(account, dimension): [value by month]}, 'prior': {month: value}, 'spec': spec}."""
    act: dict[tuple[str, str], dict[int, float]] = {}
    with open(base / "actuals.csv") as f:
        for r in csv.DictReader(f):
            act.setdefault((r["account"], r["dimension"]), {})[int(r["month"])] = float(r["value"])
    with open(base / "prior_forecast.csv") as f:
        prior = {int(r["month"]): float(r["revenue_forecast_at_jun"]) for r in csv.DictReader(f)}
    return {"act": {k: [v[m] for m in sorted(v)] for k, v in act.items()}, "prior": prior, "spec": spec()}


if __name__ == "__main__":
    write(generate())
    print("wrote", OUT.relative_to(REPO))
    sys.exit(0)
