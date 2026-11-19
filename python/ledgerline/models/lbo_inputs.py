"""Inputs for workbook 03 (LBO), shared by the generator and the reference (ADR 0005)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import yaml

from ..data.history import load
from ..data.normalise import History
from .assumptions import CASES, fade

REPO = Path(__file__).resolve().parents[3]
M = 1e6


@dataclass
class LBOInputs:
    spec: dict
    history: History
    n_hist: int
    n_fcst: int
    tx: dict[str, float]
    j: dict[str, float]
    rates: dict[str, list[float]]
    drivers: dict[str, dict[str, list[float]]]
    src: dict[str, str]
    scenario: int = 1

    @property
    def ticker(self) -> str:
        return self.spec["ticker"]

    @property
    def hist_slice(self) -> range:
        n = len(self.history.period_ends)
        return range(n - self.n_hist, n)

    def labels(self) -> list[str]:
        last = self.history.period_ends[-1]
        return [self.history.fy_labels()[i] for i in self.hist_slice] + [f"FY{last.year + k}" for k in range(1, self.n_fcst + 1)]

    def period_ends(self) -> list[str]:
        last = self.history.period_ends[-1]
        return [self.history.period_ends[i].isoformat() for i in self.hist_slice] + \
               [(last + timedelta(days=365 * k)).isoformat() for k in range(1, self.n_fcst + 1)]

    def h(self, key: str) -> list[float]:
        return [self.history.values[key][i] / M for i in self.hist_slice]

    def live(self, d: str) -> list[float]:
        return self.drivers[d][CASES[self.scenario - 1]]

    def nwc_hist(self) -> list[float]:
        h = self.h
        return [a + b + c - d - (e + f + g + k) for a, b, c, d, e, f, g, k in zip(
            h("receivables"), h("inventory"), h("other_current_assets"), h("accounts_payable"),
            h("accrued_liabilities"), h("employee_liabilities"), h("deferred_revenue"), h("other_current_liabilities"))]


def build_lbo_inputs(scenario: int = 1) -> LBOInputs:
    spec = yaml.safe_load((REPO / "spec" / "SKX_LBO.yaml").read_text())
    h = load(spec["ticker"])
    n_f = spec["forecast_years"]
    src = {}
    tx = {}
    for k, v in spec["transaction"].items():
        tx[k] = float(v["value"])
        src[k] = f"{v['src']} (accession {spec['accession']})"
    jd = {}
    for k, v in spec["judgement"].items():
        jd[k] = float(v["value"])
        src[k] = v["src"]
    rates = {k: [float(x) for x in v["values"]] for k, v in spec["rates"].items()}
    for k, v in spec["rates"].items():
        src[k] = v["src"]
    drivers = {}
    for name, d in spec["drivers"].items():
        bs, be = d["base"]["start"], d["base"]["end"]
        drivers[name] = {"base": fade(bs, be, n_f)}
        for case in ("upside", "downside"):
            drivers[name][case] = fade(bs + d[case]["start"], be + d[case]["end"], n_f)
        src[name] = d["rationale"]
    return LBOInputs(spec, h, spec["history_years"], n_f, tx, jd, rates, drivers, src, scenario)
