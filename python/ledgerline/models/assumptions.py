"""Resolve a company spec (spec/<TICKER>.yaml) into concrete per-year scenario inputs.

The result is the *input set* shared by the Excel generator and the Python reference model.
Both consume the same inputs and compute everything else independently (ADR 0005).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from ..data.history import load, load_maturities
from ..data.normalise import History

REPO = Path(__file__).resolve().parents[3]
CASES = ("base", "upside", "downside")
M = 1e6  # model units: $ millions, shares in millions


def hist_ratios(h: History) -> dict[str, list[float | None]]:
    """Driver values implied by each historical year (None where undefined)."""
    v, n = h.values, len(h.period_ends)

    def debt(i):
        return v["current_debt"][i] + v["lt_debt"][i] + v["short_term_debt"][i]

    out: dict[str, list[float | None]] = {k: [None] * n for k in (
        "store_openings", "sales_per_store_growth", "gross_margin", "sga_pct", "other_opex_pct", "da_pct_ppe",
        "capex_pct", "tax_rate", "receivable_days", "inventory_days", "payable_days", "oca_pct", "ocl_pct",
        "sbc_pct", "debt_rate", "cash_rate", "payout_ratio", "buyback_pct", "share_price_growth")}
    for i in range(n):
        rev, cogs = v["revenue"][i], v["cogs"][i]
        out["gross_margin"][i] = 1 - cogs / rev
        out["sga_pct"][i] = v["sga"][i] / rev
        out["other_opex_pct"][i] = v["other_opex"][i] / rev
        out["capex_pct"][i] = -v["capex"][i] / rev
        out["tax_rate"][i] = v["income_tax"][i] / v["pretax_income"][i]
        out["receivable_days"][i] = v["receivables"][i] / rev * 365
        out["inventory_days"][i] = v["inventory"][i] / cogs * 365
        out["payable_days"][i] = v["accounts_payable"][i] / cogs * 365
        out["oca_pct"][i] = v["other_current_assets"][i] / rev
        out["ocl_pct"][i] = ocl(h, i) / rev
        out["sbc_pct"][i] = v["sbc"][i] / rev
        out["payout_ratio"][i] = -v["dividends"][i] / v["net_income"][i]
        out["buyback_pct"][i] = -v["buybacks"][i] / v["net_income"][i]
        if i > 0:
            out["store_openings"][i] = v["stores"][i] - v["stores"][i - 1]
            out["da_pct_ppe"][i] = v["da"][i] / v["ppe_net"][i - 1]
            out["debt_rate"][i] = v["interest_expense"][i] / ((debt(i) + debt(i - 1)) / 2)
            out["cash_rate"][i] = v["other_nonop_income"][i] / ((v["cash"][i] + v["cash"][i - 1]) / 2)
        if i > 1:
            s = lambda j: (v["stores"][j] + v["stores"][j - 1]) / 2
            out["sales_per_store_growth"][i] = (rev / s(i)) / (v["revenue"][i - 1] / s(i - 1)) - 1
    return out


def ocl(h: History, i: int) -> float:
    v = h.values
    return (v["accrued_liabilities"][i] + v["employee_liabilities"][i] + v["deferred_revenue"][i]
            + v["other_current_liabilities"][i])


@dataclass
class Inputs:
    ticker: str
    spec: dict
    history: History                      # full fixture history (10y for the modelled company)
    n_hist: int                           # history columns shown in the model
    n_fcst: int
    drivers: dict[str, dict[str, list[float]]]   # driver -> case -> per-forecast-year values
    constants: dict[str, float]
    maturities: list[float]               # $m scheduled repayments, forecast years 1..n
    maturity_sources: list[str]
    share_price: float                    # $/share at snapshot
    share_price_source: str
    scenario: int = 1                     # 1 base, 2 upside, 3 downside
    circ: int = 0                         # 1 = interest on average balances (circular)
    notes: dict[str, str] = field(default_factory=dict)

    @property
    def hist_slice(self) -> range:
        n = len(self.history.period_ends)
        return range(n - self.n_hist, n)

    def labels(self) -> list[str]:
        last = self.history.period_ends[-1]
        return [self.history.fy_labels()[i] for i in self.hist_slice] + [f"FY{last.year + k}" for k in range(1, self.n_fcst + 1)]

    def period_ends(self) -> list[str]:
        last = self.history.period_ends[-1]
        hist = [self.history.period_ends[i].isoformat() for i in self.hist_slice]
        return hist + [(last + timedelta(days=364 * k)).isoformat() for k in range(1, self.n_fcst + 1)]

    def live(self, driver: str) -> list[float]:
        return self.drivers[driver][CASES[self.scenario - 1]]

    def h(self, key: str) -> list[float]:
        """History for the model's history columns, in model units."""
        unit_free = key in ("eps_diluted", "stores")
        return [self.history.values[key][i] / (1 if unit_free else M) for i in self.hist_slice]


def _resolve(val, ratios: list[float | None]) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    defined = [x for x in ratios if x is not None]
    if val == "last":
        return defined[-1]
    if val == "avg5":
        return sum(defined[-5:]) / len(defined[-5:])
    raise ValueError(f"unknown calibration keyword {val!r}")


def fade(start: float, end: float, n: int) -> list[float]:
    if n == 1:
        return [start]
    return [start + (end - start) * k / (n - 1) for k in range(n)]


def build_inputs(ticker: str, scenario: int = 1, circ: int = 0) -> Inputs:
    spec = yaml.safe_load((REPO / "spec" / f"{ticker.upper()}.yaml").read_text())
    h = load(ticker)
    ratios = hist_ratios(h)
    n_f = spec["forecast_years"]
    drivers: dict[str, dict[str, list[float]]] = {}
    notes: dict[str, str] = {}
    for name, d in spec["drivers"].items():
        bs, be = _resolve(d["base"]["start"], ratios[name]), _resolve(d["base"]["end"], ratios[name])
        drivers[name] = {"base": fade(bs, be, n_f)}
        for case in ("upside", "downside"):
            drivers[name][case] = fade(bs + d[case]["start"], be + d[case]["end"], n_f)
        notes[name] = " ".join(d["rationale"].split())
    consts = {k: float(c["value"]) for k, c in spec["constants"].items()}
    for k, c in spec["constants"].items():
        notes[k] = c["rationale"]

    mat = load_maturities(ticker)
    maturities, msrc = [0.0] * n_f, [""] * n_f
    if mat:
        vals = [m["value"] / M for m in mat["maturities"]]
        for k in range(5):
            maturities[k], msrc[k] = vals[k], f"{mat['maturities'][k]['tag']}@{mat['maturities'][k]['accn']}"
        tail = vals[5] / max(n_f - 5, 1)
        for k in range(5, n_f):
            maturities[k] = tail
            msrc[k] = f"After-year-five maturities ({vals[5]:,.0f}) spread evenly over years 6-{n_f}. Judgement."

    from ..data.prices import load as load_prices
    px = load_prices()[ticker.upper()]
    return Inputs(ticker.upper(), spec, h, spec["model_history_years"], n_f, drivers, consts, maturities, msrc,
                  px["close"], f"{px['source']} {px['date']}", scenario, circ, notes)
