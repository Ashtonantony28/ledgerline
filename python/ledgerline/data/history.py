"""Build, save and load normalised history snapshots (fixtures/<TICKER>/).

    python -m ledgerline.data.history COST WMT ...   # fetch (cached), normalise, tie out, save

A snapshot is three committed files:
  history.csv   line items x fiscal years, in USD (shares and EPS in their own units)
  sources.csv   same shape, the XBRL tag@accession (or derived/plug/default/override) per cell
  meta.json     entity, period ends, raw-file SHA-256, tie-out summary
plus tieout.md, the human-readable tie-out report. Regenerating a snapshot is a reviewed change.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from . import edgar
from .normalise import History, normalise
from .tieout import report, tieout

FIXTURES = edgar.REPO / "fixtures"
YEARS = {"COST": 10}  # the modelled company keeps 10 years; comps keep 5
DEFAULT_YEARS = 5


def build(ticker: str, refresh: bool = False) -> History:
    ticker = ticker.upper()
    facts = edgar.fetch_companyfacts(ticker, refresh=refresh)
    ov_path = FIXTURES / ticker / "overrides.yaml"
    overrides = yaml.safe_load(ov_path.read_text()) if ov_path.exists() else None
    return normalise(ticker, facts, years=YEARS.get(ticker, DEFAULT_YEARS), overrides=overrides)


def save(h: History) -> Path:
    out = FIXTURES / h.ticker
    out.mkdir(parents=True, exist_ok=True)
    labels = h.fy_labels()
    for name, table in (("history.csv", h.values), ("sources.csv", h.source)):
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["statement", "item", *labels])
            for stmt, key in h.items:
                row = table[key]
                w.writerow([stmt, key, *(repr(x) if isinstance(x, float) else x for x in row)])
    checks = tieout(h)
    meta = {
        "ticker": h.ticker,
        "entity": h.entity,
        "period_ends": [d.isoformat() for d in h.period_ends],
        "raw_sha256": edgar.sha256_of(h.ticker) if edgar.raw_path(h.ticker).exists() else None,
        "hard_checks_pass": all(c.ok for c in checks if c.hard),
        "warnings": sum(1 for c in checks if not c.hard and not c.ok),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (out / "tieout.md").write_text(report(h, checks) + "\n")
    return out


MATURITY_TAGS = [
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive",
    "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive",
]


def save_maturities(h: History) -> None:
    """Scheduled debt maturities from the latest 10-K (debt footnote), if tagged."""
    facts = edgar.fetch_companyfacts(h.ticker)["facts"]["us-gaap"]
    end = h.period_ends[-1].isoformat()
    out = []
    for tag in MATURITY_TAGS:
        hits = [f for f in facts.get(tag, {}).get("units", {}).get("USD", []) if f.get("form") == "10-K" and f["end"] == end]
        if not hits:
            return
        f = max(hits, key=lambda f: f["filed"])
        out.append({"tag": tag, "value": float(f["val"]), "accn": f["accn"]})
    (FIXTURES / h.ticker / "maturities.json").write_text(json.dumps({"as_of": end, "maturities": out}, indent=2) + "\n")


def load_maturities(ticker: str) -> dict | None:
    p = FIXTURES / ticker.upper() / "maturities.json"
    return json.loads(p.read_text()) if p.exists() else None


def load(ticker: str) -> History:
    d = FIXTURES / ticker.upper()
    meta = json.loads((d / "meta.json").read_text())
    values: dict[str, list[float]] = {}
    source: dict[str, list[str]] = {}
    items: list[tuple[str, str]] = []
    with open(d / "history.csv") as f:
        r = csv.reader(f)
        next(r)
        for stmt, key, *vals in r:
            values[key] = [float(v) for v in vals]
            items.append((stmt, key))
    with open(d / "sources.csv") as f:
        r = csv.reader(f)
        next(r)
        for _, key, *vals in r:
            source[key] = vals
    return History(meta["ticker"], meta["entity"], [date.fromisoformat(x) for x in meta["period_ends"]],
                   values, source, items)


def main(argv: list[str]) -> int:
    refresh = "--refresh" in argv
    tickers = [a for a in argv if not a.startswith("--")] or list(edgar.CIKS)
    bad = 0
    for t in tickers:
        h = build(t, refresh=refresh)
        out = save(h)
        save_maturities(h)
        meta = json.loads((out / "meta.json").read_text())
        status = "OK" if meta["hard_checks_pass"] else "TIE-OUT FAILED"
        bad += not meta["hard_checks_pass"]
        print(f"{t}: {h.fy_labels()[0]}..{h.fy_labels()[-1]} {status}, {meta['warnings']} warnings -> {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
