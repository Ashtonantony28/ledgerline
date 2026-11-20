"""Inputs for workbook 04 (M&A), shared by the generator and the reference (ADR 0005)."""
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
RAW_UNITS = {"eps_diluted"}  # stored per share, not in dollars


@dataclass
class MnAInputs:
    spec: dict
    acq: History
    tgt: History
    n_hist: int
    n_fcst: int
    tx: dict[str, float]
    j: dict[str, float]
    structures: dict[str, list[float]]
    structure_names: list[str]
    syn_runrate: dict[str, float]
    syn_phase: list[float]
    syn_costs: list[float]
    fl_proj: dict[str, dict[str, list[float]]]
    drivers: dict[str, dict[str, list[float]]]
    src: dict[str, str]
    scenario: int = 1
    structure: int = 3

    @property
    def history(self) -> History:  # the acquirer, for the shared cover sheet
        return self.acq

    @property
    def ticker(self) -> str:
        return f"{self.spec['acquirer']} / {self.spec['target']}"

    @property
    def case(self) -> str:
        return CASES[self.scenario - 1]

    @property
    def hist_slice(self) -> range:
        n = len(self.acq.period_ends)
        return range(n - self.n_hist, n)

    def _label(self, d) -> str:
        # Retail 52/53-week years are named by the calendar year they start in: FY2024 ends 1 Feb 2025.
        y = d.year - 1 if self.spec.get("fy_naming") == "start_year" and d.month <= 2 else d.year
        return f"FY{y}"

    def labels(self) -> list[str]:
        last = self.acq.period_ends[-1]
        hist = [self._label(self.acq.period_ends[i]) for i in self.hist_slice]
        y0 = int(hist[-1][2:])
        return hist + [f"FY{y0 + k}" for k in range(1, self.n_fcst + 1)]

    def period_ends(self) -> list[str]:
        last = self.acq.period_ends[-1]
        return [self.acq.period_ends[i].isoformat() for i in self.hist_slice] + \
               [(last + timedelta(days=364 * k)).isoformat() for k in range(1, self.n_fcst + 1)]

    def _h(self, h: History, key: str) -> list[float]:
        div = 1.0 if key in RAW_UNITS else M
        return [h.values[key][i] / div for i in self.hist_slice]

    def ha(self, key: str) -> list[float]:
        return self._h(self.acq, key)

    def ht(self, key: str) -> list[float]:
        return self._h(self.tgt, key)

    def live(self, d: str) -> list[float]:
        return self.drivers[d][self.case]

    def pct_stock(self) -> float:
        return self.structures["pct_stock"][self.structure - 1]

    def dks_price(self) -> float:
        return self.structures["dks_price"][self.structure - 1]


def build_mna_inputs(scenario: int = 1, structure: int = 3) -> MnAInputs:
    spec = yaml.safe_load((REPO / "spec" / "DKS_FL_MA.yaml").read_text())
    acq, tgt = load(spec["acquirer"]), load(spec["target"])
    n_h, n_f = spec["history_years"], spec["forecast_years"]
    assert [acq.period_ends[i] for i in range(-n_h, 0)][-1] == tgt.period_ends[-1], "fiscal years must align"
    src: dict[str, str] = {}
    tx = {}
    for k, v in spec["transaction"].items():
        tx[k] = float(v["value"])
        src[k] = v["src"]
    jd = {}
    for k, v in spec["judgement"].items():
        jd[k] = float(v["value"])
        src[k] = v["src"]
    st = {k: [float(x) for x in spec["structures"][k]["values"]] for k in ("pct_stock", "dks_price")}
    for k in st:
        src[k] = spec["structures"][k]["src"]
    sy = spec["synergies"]
    runrate = {c: float(sy["runrate"][c]) for c in CASES}
    src["syn_runrate"], src["syn_phase"], src["syn_costs"] = sy["runrate"]["src"], sy["phase"]["src"], sy["costs"]["src"]
    proj = {}
    for c in CASES:
        p = spec["fl_projections"][c]
        proj[c] = {"revenue": [float(x) for x in p["revenue"]], "ebitda": [float(x) for x in p["ebitda"]]}
        src[f"fl_proj_{c}"] = p["src"]
    drivers = {}
    for name, d in spec["drivers"].items():
        bs, be = d["base"]["start"], d["base"]["end"]
        drivers[name] = {"base": fade(bs, be, n_f)}
        for case in ("upside", "downside"):
            drivers[name][case] = fade(bs + d[case]["start"], be + d[case]["end"], n_f)
        src[name] = d["rationale"]
    return MnAInputs(spec, acq, tgt, n_h, n_f, tx, jd, st, list(spec["structures"]["names"]), runrate,
                     [float(x) for x in sy["phase"]["values"]], [float(x) for x in sy["costs"]["values"]],
                     proj, drivers, src, scenario, structure)
