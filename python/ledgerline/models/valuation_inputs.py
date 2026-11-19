"""Inputs for workbook 02 (DCF + comps), shared by the generator and the reference (ADR 0005)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from ..data.history import FIXTURES, load
from ..data.prices import load as load_prices
from .assumptions import Inputs

M = 1e6


@dataclass
class Comp:
    ticker: str
    name: str
    fy: str
    period_end: str
    price: float
    shares_out: float      # millions
    revenue: float
    ebitda: float
    net_income: float
    eps: float
    debt: float
    cash: float            # cash + short-term investments
    nci: float
    sources: dict


@dataclass
class ValInputs:
    rf: float
    erp: float
    beta_raw: float
    blume_w: float
    credit_spread: float
    marginal_tax: float
    terminal_growth: float
    midyear_adj: float
    wacc_step: float
    growth_step: float
    multiple_step: float
    shares_out: float      # target's cover-page shares, millions
    price: float
    price_date: str
    years_since_fye: float
    hi_52w: float
    lo_52w: float
    comps: list[Comp]
    notes: dict


def comp_from_fixture(ticker: str, prices: dict) -> Comp:
    h = load(ticker)
    i = len(h.period_ends) - 1
    v = lambda k: h.values[k][i] / M
    px = prices[ticker]
    return Comp(ticker, h.entity, h.fy_labels()[i], h.period_ends[i].isoformat(), px["close"], px["shares_out"] / M,
                v("revenue"), v("operating_income") + v("da"), v("net_income"), h.values["eps_diluted"][i],
                v("short_term_debt") + v("current_debt") + v("lt_debt"), v("cash") + v("st_investments"), v("nci_equity"),
                {"history": f"fixtures/{ticker}/history.csv ({h.fy_labels()[i]}, period end {h.period_ends[i]})",
                 "price": f"{px['source']} {px['date']}", "shares": px["shares_source"]})


def build_val_inputs(inp: Inputs) -> ValInputs:
    spec = inp.spec["valuation"]
    mk = json.loads((FIXTURES / "market.json").read_text())
    prices = load_prices()
    t = mk["tickers"][inp.ticker]
    px = prices[inp.ticker]
    fye = inp.history.period_ends[-1]
    yrs = (date.fromisoformat(px["date"]) - fye).days / 365
    c = lambda k: float(spec[k]["value"])
    notes = {k: spec[k]["rationale"] for k in spec if isinstance(spec[k], dict)}
    notes.update({
        "rf": f"{mk['risk_free']['source']}, {mk['risk_free']['date']}",
        "erp": f"{mk['erp']['source']}, {mk['erp']['date']}",
        "beta_raw": f"{t['beta']['source']}, window {t['beta']['window']}",
        "shares_out": px["shares_source"],
        "price": f"{px['source']} {px['date']}",
        "years_since_fye": f"Days from fiscal year end {fye} to price date {px['date']} / 365; equity value is rolled forward at the cost of equity.",
        "52w": t["range_52w"]["source"],
    })
    return ValInputs(mk["risk_free"]["value"], mk["erp"]["value"], t["beta"]["value"], c("blume_weight_raw"),
                     c("credit_spread"), c("marginal_tax"), c("terminal_growth"), c("midyear_adj"), c("wacc_step"),
                     c("growth_step"), c("multiple_step"), px["shares_out"] / M, px["close"], px["date"], yrs,
                     t["range_52w"]["high"], t["range_52w"]["low"],
                     [comp_from_fixture(x, prices) for x in spec["comps"]], notes)
