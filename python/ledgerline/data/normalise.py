"""Normalise XBRL company facts into the Ledgerline standard chart (ADR 0004).

Selection rules:
  * Only 10-K / 10-K/A facts are used.
  * Flow items must cover an annual period (350-380 days, which admits 52/53-week years).
  * Instant items are taken at fiscal year-end dates (the period ends of annual revenue).
  * When several filings report the same item and period, the latest-filed value wins, so
    comparatives reflect restatements. Every chosen value records its accession number.

The result is a `History`: ordered fiscal-year end dates, values per line item, provenance,
and a tie-out report (see `tieout`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

TAGMAP_PATH = Path(__file__).with_name("tagmap.yaml")
ANNUAL_MIN_DAYS, ANNUAL_MAX_DAYS = 350, 380
STATEMENTS = ("income_statement", "balance_sheet", "cash_flow", "operating_kpis")


def load_tagmap() -> dict:
    return yaml.safe_load(TAGMAP_PATH.read_text())


def line_items(tagmap: dict | None = None) -> list[tuple[str, str, dict]]:
    tagmap = tagmap or load_tagmap()
    return [(stmt, key, spec) for stmt in STATEMENTS for key, spec in tagmap[stmt].items()]


_TOKEN = re.compile(r"\s*([+-])?\s*([a-z_][a-z0-9_]*)")


def eval_linear(expr: str, values: dict[str, float]) -> float:
    """Evaluate 'a - b + c' style expressions over line-item values."""
    total, pos = 0.0, 0
    expr = expr.strip()
    first = True
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or (not first and m.group(1) is None):
            raise ValueError(f"bad expression {expr!r} at {pos}")
        sign = -1.0 if m.group(1) == "-" else 1.0
        total += sign * values[m.group(2)]
        pos, first = m.end(), False
    return total


def expr_names(expr: str) -> list[str]:
    return [m.group(2) for m in _TOKEN.finditer(expr)]


@dataclass
class History:
    ticker: str
    entity: str
    period_ends: list[date]
    values: dict[str, list[float]]
    source: dict[str, list[str]]  # "tag@accn", "derived", "plug" or "default" per cell
    items: list[tuple[str, str]] = field(default_factory=list)  # (statement, key) in order

    def fy_labels(self) -> list[str]:
        return [f"FY{d.year}" for d in self.period_ends]

    def get(self, key: str, i: int) -> float:
        return self.values[key][i]


def _facts_by_period(facts: dict, tag: str, unit: str, kind: str) -> dict[date, tuple[float, str, str]]:
    """Map period end -> (value, accn, filed) using the latest-filed annual 10-K fact."""
    out: dict[date, tuple[float, str, str]] = {}
    node = facts.get("us-gaap", {}).get(tag)
    if not node:
        return out
    if unit == "*":  # count-type facts use company-specific unit names
        unit = next(iter(node["units"]))
    if unit not in node["units"]:
        return out
    for f in node["units"][unit]:
        if f.get("form") not in ("10-K", "10-K/A"):
            continue
        end = date.fromisoformat(f["end"])
        if kind == "flow":
            if "start" not in f:
                continue
            days = (end - date.fromisoformat(f["start"])).days
            if not ANNUAL_MIN_DAYS <= days <= ANNUAL_MAX_DAYS:
                continue
        elif "start" in f:
            continue
        prev = out.get(end)
        if prev is None or f["filed"] > prev[2]:
            out[end] = (float(f["val"]), f["accn"], f["filed"])
    return out


def fiscal_year_ends(facts: dict, tagmap: dict) -> list[date]:
    ends: set[date] = set()
    for tag in tagmap["income_statement"]["revenue"]["tags"]:
        ends |= set(_facts_by_period(facts, tag, "USD", "flow"))
    return sorted(ends)


def normalise(ticker: str, facts: dict, years: int = 10, overrides: dict | None = None,
              max_end: date | None = None) -> History:
    entity = facts.get("entityName", ticker)
    facts = facts.get("facts", facts)  # accept the full companyfacts document
    tagmap = load_tagmap()
    items = line_items(tagmap)
    ends_all = fiscal_year_ends(facts, tagmap)
    # Require a balance sheet at the year end so every period is a complete set.
    bs_ends = set(_facts_by_period(facts, "Assets", "USD", "instant"))
    ends = [e for e in ends_all if e in bs_ends and (max_end is None or e <= max_end)][-years:]
    overrides = overrides or {}

    values: dict[str, list[float | None]] = {}
    source: dict[str, list[str]] = {}
    for _, key, spec in items:
        values[key] = [None] * len(ends)
        source[key] = [""] * len(ends)
        if "plug" in spec:
            continue
        unit = spec.get("unit", "USD")
        sign = spec.get("sign", 1)
        for tag in spec.get("tags", []):
            by_period = _facts_by_period(facts, tag, unit, spec["kind"])
            for i, e in enumerate(ends):
                if values[key][i] is None and e in by_period:
                    v, accn, _ = by_period[e]
                    values[key][i] = sign * v
                    source[key][i] = f"{tag}@{accn}"

    for key, per_period in overrides.items():
        for label, ov in per_period.items():
            i = [f"FY{e.year}" for e in ends].index(label)
            values[key][i] = float(ov["value"])
            source[key][i] = f"override: {ov['citation']}"

    # Resolve derives (may chain), then defaults, then plugs.
    for _ in range(4):
        for _, key, spec in items:
            if "derive" not in spec:
                continue
            for i in range(len(ends)):
                if values[key][i] is not None:
                    continue
                env = {n: values[n][i] for n in expr_names(spec["derive"])}
                if all(v is not None for v in env.values()):
                    values[key][i] = eval_linear(spec["derive"], env)
                    source[key][i] = "derived"
        for _, key, spec in items:
            if "default" in spec:
                for i in range(len(ends)):
                    if values[key][i] is None and not _derivable_later(spec, values, i):
                        values[key][i] = float(spec["default"])
                        source[key][i] = "default"
    for _, key, spec in items:
        if "plug" in spec:
            for i in range(len(ends)):
                env = {n: values[n][i] for n in expr_names(spec["plug"])}
                if any(v is None for v in env.values()):
                    missing = [n for n, v in env.items() if v is None]
                    raise ValueError(f"{ticker} {ends[i]}: cannot compute plug {key}; missing {missing}")
                values[key][i] = eval_linear(spec["plug"], env)
                source[key][i] = "plug"

    missing = [(k, f"FY{ends[i].year}") for k, vs in values.items() for i, v in enumerate(vs) if v is None]
    if missing:
        raise ValueError(f"{ticker}: unresolved line items {missing[:10]}")
    return History(
        ticker=ticker.upper(),
        entity=entity,
        period_ends=ends,
        values={k: [float(x) for x in v] for k, v in values.items()},
        source=source,
        items=[(s, k) for s, k, _ in items],
    )


def _derivable_later(spec: dict, values: dict, i: int) -> bool:
    if "derive" not in spec:
        return False
    return all(values[n][i] is not None for n in expr_names(spec["derive"]))
