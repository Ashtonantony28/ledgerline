"""Interface exports to other projects (plan section 10).

    python -m ledgerline.exports        # rewrite exports/*.csv (a reviewed change; tests fail if they are stale)

borrower_spreads.csv   -> banking-risk project (PD/LGD and rating models): one row per borrower, from ref/credit.py.
fundamental_signals.csv -> Tickforge alpha research: one row per company and fiscal year, with the date from which the
                           row may be used (fiscal year end + a conservative filing lag).
Schemas and versioning rules: docs/interfaces/.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

from .data.edgar import CIKS
from .data.history import load, load_maturities
from .ref import credit

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "exports"
SCHEMA_VERSION = "1.1"  # 1.1 (additive): sic, maturities; companion history and PD-table files

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
    ("sic", "str", "SEC SIC code", None), ("sic_description", "str", "", None),
    ("debt_due_1y", "float", "$m", None), ("debt_due_after_1y", "float", "$m", None), ("wam_years", "float", "years", None),
]
HISTORY_DROP = ("debt_due_1y", "debt_due_after_1y", "wam_years")  # maturity tables exist for the latest 10-K only
PD_COLUMNS = [("schema_version", "str", ""), ("band", "int", "1 = best"), ("rating", "str", "band label"),
              ("pd_1y", "float", "probability"), ("leverage_upper_bound", "float", "x, blank for the last band"),
              ("coverage_lower_bound", "float", "x, blank for the last band")]
SIGNAL_COLUMNS = [
    ("schema_version", "str", ""), ("ticker", "str", ""), ("fy_end", "date", "ISO 8601"),
    ("available_from", "date", "ISO 8601, fy_end + lag"), ("revenue_growth", "float", "ratio"),
    ("gross_margin", "float", "ratio"), ("operating_margin", "float", "ratio"), ("fcf_margin", "float", "ratio"),
    ("accruals_ratio", "float", "(net income - CFO) / average total assets"), ("roa", "float", "net income / average total assets"),
    ("lease_adj_leverage", "float", "x"), ("source_accession", "str", "accession of the filing that last reported revenue"),
]


SIC = json.loads((REPO / "fixtures" / "sic.json").read_text())  # data.sec.gov/submissions, fetched 2026-11-20


def maturity(ticker: str, debt: float, sp: dict) -> dict:
    """Amounts due within / after one year and weighted-average maturity, from the latest 10-K maturity table."""
    mt = load_maturities(ticker)
    if not mt:
        return {"debt_due_1y": "", "debt_due_after_1y": "", "wam_years": ""}
    vals = [x["value"] / 1e6 for x in mt["maturities"]]
    mids = sp["maturity"]["bucket_mid_years"] + [sp["maturity"]["after_year5_years"]]
    tot = sum(vals)
    return {"debt_due_1y": vals[0], "debt_due_after_1y": debt - vals[0],
            "wam_years": sum(v * t for v, t in zip(vals, mids)) / tot if tot else ""}


def _row(b, x, sp: dict, with_maturity: bool) -> dict:
    row = {"schema_version": SCHEMA_VERSION, "cik": CIKS[b.ticker], "revenue": b.v["revenue"], "debt": b.v["debt"],
           "leases": b.v["leases"], "sic": SIC[b.ticker]["sic"], "sic_description": SIC[b.ticker]["sic_description"]}
    for col, _, _, key in SPREAD_COLUMNS:
        if key:
            row[col] = x[key]
    if with_maturity:
        row.update(maturity(b.ticker, b.v["debt"], sp))
    return row


def borrower_rows() -> list[dict]:
    r = credit.run()
    return [_row(b, x, r["spec"], True) for b, x in zip(r["borrowers"], r["results"])]


def borrower_history_rows() -> list[dict]:
    sp = credit.spec()
    return [_row(b, credit.analyse(b, sp), sp, False) for b in credit.borrower_years(sp)]


def pd_rows() -> list[dict]:
    sc = credit.spec()["scorecard"]
    n = len(sc["ratings"])
    return [{"schema_version": SCHEMA_VERSION, "band": k + 1, "rating": sc["ratings"][k], "pd_1y": sc["pd_1y"][k],
             "leverage_upper_bound": sc["leverage_bounds"][k] if k < n - 1 else "",
             "coverage_lower_bound": sc["coverage_bounds"][k] if k < n - 1 else ""} for k in range(n)]


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
            w.writerow(["" if isinstance(r[c], float) and math.isinf(r[c]) else f"{r[c]:.10g}" if isinstance(r[c], float) else r[c]
                        for c in cols])


def write(out: Path = OUT) -> list[Path]:
    files = {"borrower_spreads.csv": ([c[0] for c in SPREAD_COLUMNS], borrower_rows()),
             "borrower_spreads_history.csv": ([c[0] for c in SPREAD_COLUMNS if c[0] not in HISTORY_DROP], borrower_history_rows()),
             "pd_table.csv": ([c[0] for c in PD_COLUMNS], pd_rows()),
             "fundamental_signals.csv": ([c[0] for c in SIGNAL_COLUMNS], signal_rows())}
    for name, (cols, rows) in files.items():
        _write(out / name, cols, rows)
    return [out / name for name in files]




MEANING = {
    "interest": "gross interest expense; net non-operating interest where gross is not tagged (DG, KR, LOW)",
    "adj_debt": "debt + operating lease liabilities", "net_debt": "adj_debt - cash - short-term investments",
    "fcf": "cash from operations + capex (cash sign)", "leverage": "adj_debt / EBITDA (blank if EBITDA <= 0)",
    "coverage": "EBITDA / interest (blank if no interest)", "altman_z": "Altman Z' (book-equity form)",
    "rating": "simplified scorecard band (AAA..CCC), not an agency rating", "pd_1y": "illustrative one-year PD for the band (pd_table.csv)",
    "covenant_headroom": "share of EBITDA that can be lost before the 3.5x leverage / 3.0x coverage package breaches",
    "debt_capacity": "additional adj_debt at 3.0x leverage or 4.0x coverage, whichever is lower",
    "stressed_rating": "rating after EBITDA -30% and +200bp on 30% of debt", "stressed_breach": "1 if the covenant package breaches under stress",
    "sic": "SEC SIC code (data.sec.gov submissions)", "debt_due_1y": "10-K maturity table: principal due in the next 12 months; blank if not tagged (DKS, FL)",
    "debt_due_after_1y": "debt - debt_due_1y (includes short-term borrowings, which the maturity table omits)",
    "wam_years": "weighted-average maturity: years 1-5 at mid-year, the after-year-5 bucket at 10 years (judgement)",
}


def write_docs(out: Path = REPO / "docs" / "interfaces") -> None:
    a = ["# Interface: borrower spreads (Ledgerline -> banking-risk)", "",
         f"Schema version {SCHEMA_VERSION}. Producer: `python -m ledgerline.exports` from `ref/credit.py` (the golden model of workbook 09).",
         "Units $m unless stated. Contract and freshness tests: `tests/test_credit.py`.", "",
         "Versioning: adding a column or a companion file bumps the minor version; renaming, removing or changing the meaning or unit",
         "of a column bumps the major version. Read columns by name and check `schema_version`.", "",
         "Files:", "- `borrower_spreads.csv`: one row per borrower, latest 10-K.",
         "- `borrower_spreads_history.csv`: one row per borrower per fiscal year in the fixtures, same columns without the maturity fields",
         "  (maturity tables are kept for the latest 10-K only). Before ASC 842 (fiscal years starting after 15 Dec 2018) operating leases",
         "  were off balance sheet, so `leases` is 0 and lease-adjusted leverage is not comparable across that break.",
         "- `pd_table.csv`: the band grid and illustrative PDs, so the calibration can be tested on its own.", "",
         "Not provided: secured share of debt (not consistently tagged in XBRL; the borrowers' debt is almost entirely senior unsecured notes).", "",
         "| column | type | unit | meaning |", "|---|---|---|---|"]
    a += [f"| {c} | {t} | {u} | {MEANING.get(c, '')} |" for c, t, u, _ in SPREAD_COLUMNS]
    a += ["", "pd_table.csv:", "", "| column | type | unit |", "|---|---|---|"] + [f"| {c} | {t} | {u} |" for c, t, u in PD_COLUMNS]
    (out / "borrower_spreads.md").write_text("\n".join(a) + "\n")
    b = ["# Interface: fundamental_signals.csv (Ledgerline -> Tickforge)", "",
         f"Schema version {SCHEMA_VERSION}. Producer: `python -m ledgerline.exports`. One row per company and fiscal year (the first year is",
         "dropped: growth and averages need a prior year).", "",
         "**Point-in-time caveat.** `available_from` is fiscal year end + 90 days, a conservative filing lag. The *values* are as last reported",
         "in the fixtures, which can be a later filing than the original (see `source_accession`: COST FY2018 comes from a 2020 10-K). A strict",
         "point-in-time test must either accept that restatement look-ahead or rebuild the panel from each original filing; Tickforge's",
         "\"backtests do not lie\" rule means the caveat travels with any result.", "",
         "| column | type | unit / definition |", "|---|---|---|"] + [f"| {c} | {t} | {u} |" for c, t, u in SIGNAL_COLUMNS]
    (out / "fundamental_signals.md").write_text("\n".join(b) + "\n")


if __name__ == "__main__":
    for p in write():
        print("wrote", p.relative_to(REPO))
    write_docs()
    sys.exit(0)
