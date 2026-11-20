"""Interface exports to other projects (plan section 10).

    python -m ledgerline.exports        # rewrite exports/*.csv (a reviewed change; tests fail if they are stale)

borrower_spreads.csv   -> banking-risk project (PD/LGD and rating models): one row per borrower, from ref/credit.py.
fundamental_signals.csv -> Tickforge alpha research: one row per company and fiscal year, with the date from which the
                           row may be used (fiscal year end + a conservative filing lag).
Schemas and versioning rules: docs/interfaces/.
"""
from __future__ import annotations

import csv
import sys
from datetime import timedelta
from pathlib import Path

from .data.edgar import CIKS
from .data.history import load
from .ref import credit

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "exports"
SCHEMA_VERSION = "1.0"

SPREAD_COLUMNS = [  # (column, type, unit, from the credit reference)
    ("schema_version", "str", "", None), ("ticker", "str", "", "ticker"), ("cik", "int", "", None),
    ("fy_end", "date", "ISO 8601", "fy_end"), ("revenue", "float", "$m", None), ("ebitda", "float", "$m", "ebitda"),
    ("interest", "float", "$m", "interest"), ("debt", "float", "$m", None), ("leases", "float", "$m", None),
    ("adj_debt", "float", "$m", "adj_debt"), ("net_debt", "float", "$m", "net_debt"), ("fcf", "float", "$m", "fcf"),
    ("leverage", "float", "x", "leverage"), ("coverage", "float", "x", "coverage"), ("fcf_debt", "float", "ratio", "fcf_debt"),
    ("altman_z", "float", "x", "z"), ("rating", "str", "band label", "rating"), ("pd_1y", "float", "probability", "pd"),
    ("covenant_headroom", "float", "share of EBITDA", "cushion"), ("debt_capacity", "float", "$m", "capacity"),
    ("stressed_rating", "str", "band label", "s_rating"), ("stressed_pd_1y", "float", "probability", "s_pd"),
    ("stressed_breach", "int", "0/1", "s_breach"),
]
SIGNAL_COLUMNS = [
    ("schema_version", "str", ""), ("ticker", "str", ""), ("fy_end", "date", "ISO 8601"),
    ("available_from", "date", "ISO 8601, fy_end + lag"), ("revenue_growth", "float", "ratio"),
    ("gross_margin", "float", "ratio"), ("operating_margin", "float", "ratio"), ("fcf_margin", "float", "ratio"),
    ("accruals_ratio", "float", "(net income - CFO) / average total assets"), ("roa", "float", "net income / average total assets"),
    ("lease_adj_leverage", "float", "x"), ("source_accession", "str", "accession of the filing that last reported revenue"),
]


def borrower_rows() -> list[dict]:
    r = credit.run()
    rows = []
    for b, x in zip(r["borrowers"], r["results"]):
        row = {"schema_version": SCHEMA_VERSION, "cik": CIKS[b.ticker], "revenue": b.v["revenue"], "debt": b.v["debt"],
               "leases": b.v["leases"]}
        for col, _, _, key in SPREAD_COLUMNS:
            if key:
                row[col] = x[key]
        rows.append(row)
    return rows


def signal_rows() -> list[dict]:
    lag = timedelta(days=credit.spec()["signals"]["availability_lag_days"])
    rows = []
    for t in CIKS:
        h = load(t)
        v = h.values
        for i in range(1, len(h.period_ends)):
            avg_ta = (v["total_assets"][i] + v["total_assets"][i - 1]) / 2
            rev = v["revenue"][i]
            ebitda = v["operating_income"][i] + v["da"][i]
            adj = v["current_debt"][i] + v["lt_debt"][i] + v["short_term_debt"][i] + v["op_lease_liab_current"][i] + v["op_lease_liab_noncurrent"][i]
            rows.append({
                "schema_version": SCHEMA_VERSION, "ticker": t, "fy_end": h.period_ends[i].isoformat(),
                "available_from": (h.period_ends[i] + lag).isoformat(),
                "revenue_growth": rev / v["revenue"][i - 1] - 1, "gross_margin": 1 - v["cogs"][i] / rev,
                "operating_margin": v["operating_income"][i] / rev, "fcf_margin": (v["cfo"][i] + v["capex"][i]) / rev,
                "accruals_ratio": (v["net_income"][i] - v["cfo"][i]) / avg_ta, "roa": v["net_income"][i] / avg_ta,
                "lease_adj_leverage": adj / ebitda if ebitda > 0 else float("nan"),
                "source_accession": h.source["revenue"][i].split("@")[-1],
            })
    return rows


def _write(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([f"{r[c]:.10g}" if isinstance(r[c], float) else r[c] for c in cols])


def write(out: Path = OUT) -> list[Path]:
    a, b = out / "borrower_spreads.csv", out / "fundamental_signals.csv"
    _write(a, [c[0] for c in SPREAD_COLUMNS], borrower_rows())
    _write(b, [c[0] for c in SIGNAL_COLUMNS], signal_rows())
    return [a, b]


if __name__ == "__main__":
    for p in write():
        print("wrote", p.relative_to(REPO))
    sys.exit(0)
