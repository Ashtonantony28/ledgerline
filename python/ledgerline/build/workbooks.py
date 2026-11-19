"""Compose model modules into the delivered workbooks.

    python -m ledgerline.build.workbooks            # build every workbook into workbooks/
    python -m ledgerline.build.workbooks 01         # build one

Each workbook is self-contained: a transaction workbook embeds the operating model it needs
instead of linking to another file, so there are no fragile external links (ADR 0003).
A layout sidecar (<name>.layout.json) records where every row landed, for tests and audit.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from .grid import Model
from ..models.assumptions import build_inputs, Inputs

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "workbooks"
DISCLAIMER = ("Educational portfolio model built from public SEC filings. Not investment advice. "
              "Figures may contain errors; verify against the filings before relying on them.")


def add_cover(m: Model, title: str, inp: Inputs, sheets_desc: list[tuple[str, str]], has_checks: bool = True) -> None:
    c = m.sheet("Cover", title, timeline=False)
    c.col_widths = {"A": 34, "B": 70}
    c.cell("A3", "Company"); c.cell("B3", f"{inp.history.entity} ({inp.ticker})", bold=True)
    c.cell("A4", "Units"); c.cell("B4", "$ millions unless stated; shares in millions")
    c.cell("A5", "History"); c.cell("B5", f"{inp.labels()[0]} to {inp.labels()[inp.n_hist - 1]} from 10-K XBRL (SEC EDGAR)")
    c.cell("A6", "Forecast"); c.cell("B6", f"{inp.labels()[inp.n_hist]} to {inp.labels()[-1]}")
    c.cell("A7", "Live scenario"); c.cell("B7", "='Inputs'!C%d" % m.sheets["Inputs"].row("scenario_name"), bold=True)
    c.cell("A8", "Circularity switch"); c.cell("B8", "=IF(CircSwitch=1,\"ON (iterative)\",\"OFF (opening balances)\")")
    if has_checks:
        c.cell("A9", "Model integrity")
        c.cell("B9", "=IF(MasterCheck=0,\"ALL CHECKS PASS\",\"CHECK FAILURE - see Checks sheet\")", bold=True)
    c.cell("A10", "Built"); c.cell("B10", f"{date.today().isoformat()} by the Ledgerline generator (see Log)")
    c.cell("A12", "Colour code", bold=True)
    c.cell("A13", "Blue on yellow", input=True); c.cell("B13", "Hard-coded input (every one carries a source note)")
    c.cell("A14", "Black", color="000000"); c.cell("B14", "Formula")
    c.cell("A15", "Green", color="008000"); c.cell("B15", "Direct link to another sheet")
    c.cell("A16", "Grey shading"); c.cell("B16", "Forecast columns")
    c.cell("A18", "Sheets", bold=True)
    for k, (name, desc) in enumerate(sheets_desc):
        c.cell(f"A{19 + k}", name, bold=True); c.cell(f"B{19 + k}", desc)
    r = 20 + len(sheets_desc)
    c.cell(f"A{r}", "Disclaimer", bold=True); c.cell(f"B{r}", DISCLAIMER, wrap=True)


def add_log(m: Model, entries: list[tuple[str, str]]) -> None:
    lg = m.sheet("Log", "Change log", timeline=False)
    lg.col_widths = {"A": 14, "B": 100}
    lg.cell("A3", "Date", bold=True); lg.cell("B3", "Change", bold=True)
    for k, (d, text) in enumerate(entries):
        lg.cell(f"A{4 + k}", d); lg.cell(f"B{4 + k}", text, wrap=True)


def _reorder(m: Model, first: list[str]) -> None:
    m.sheets = {k: m.sheets[k] for k in first + [k for k in m.sheets if k not in first]}


THREE_STATEMENT_SHEETS = [
    ("Inputs", "Scenario selector, circularity switch, constants"),
    ("Hist", "Normalised 10-K history (blue, sourced per cell)"),
    ("Scenarios", "Base / upside / downside driver paths (analyst judgement, rationale in notes)"),
    ("Drivers", "Live drivers: implied history and selected-scenario forecast"),
    ("Schedules", "Revenue build, PP&E, working capital, debt and revolver, equity and shares"),
    ("IS", "Income statement"), ("BS", "Balance sheet"), ("CF", "Cash flow statement"),
    ("Ratios", "Margins, returns, leverage"), ("Checks", "Integrity checks and master flag"),
]


def build_01(ticker: str = "COST", scenario: int = 1, circ: int = 0, out: Path | None = None) -> tuple[Path, dict]:
    from ..models.three_statement import add_three_statement, timeline
    inp = build_inputs(ticker, scenario=scenario, circ=circ)
    m = Model(timeline(inp), f"{ticker} three-statement model")
    add_three_statement(m, inp)
    add_cover(m, f"{inp.history.entity}: three-statement operating model", inp, THREE_STATEMENT_SHEETS)
    add_log(m, [(date.today().isoformat(), "Generated from spec/%s.yaml and fixtures/%s (M2)." % (ticker, ticker))])
    _reorder(m, ["Cover"])
    path = Path(out or OUT / f"01_{ticker}_ThreeStatement.xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)
    layout = m.save(path)
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


def build_00(out: Path | None = None) -> tuple[Path, dict]:
    from ..models.data_workbook import build_00 as _b
    from ..data.edgar import CIKS
    path = Path(out or OUT / "00_Data.xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)
    return _b(list(CIKS), path), {}


VALUATION_SHEETS = THREE_STATEMENT_SHEETS[:-1] + [
    ("WACC", "Cost of capital: CAPM with market inputs, after-tax cost of debt, market-value weights"),
    ("Comps", "Trading comparables and statistics"),
    ("DCF", "Unlevered DCF: perpetuity-growth and exit-multiple methods, reverse DCF"),
    ("Sensitivity", "Implied price grids: WACC x terminal growth, WACC x exit multiple"),
    ("Football", "Valuation summary range chart"),
    ("Checks", "Integrity checks and master flag"),
]


def build_02(ticker: str = "COST", scenario: int = 1, out: Path | None = None) -> tuple[Path, dict]:
    from ..models.three_statement import add_three_statement, timeline
    from ..models.valuation import add_valuation, valuation_checks
    from ..models.valuation_inputs import build_val_inputs
    inp = build_inputs(ticker, scenario=scenario, circ=0)
    v = build_val_inputs(inp)
    m = Model(timeline(inp), f"{ticker} valuation")
    add_three_statement(m, inp, extra_checks=valuation_checks())
    add_valuation(m, inp, v)
    add_cover(m, f"{inp.history.entity}: DCF and trading comps", inp, VALUATION_SHEETS)
    add_log(m, [(date.today().isoformat(), "Generated from spec/%s.yaml, fixtures/%s, fixtures/market.json (M3)." % (ticker, ticker))])
    order = ["Cover"] + [n for n, _ in VALUATION_SHEETS]
    _reorder(m, order)
    path = Path(out or OUT / f"02_{ticker}_Valuation.xlsx")
    layout = m.save(path)
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


BUILDERS = {"00": build_00, "01": build_01, "02": build_02}


def main(argv: list[str]) -> int:
    for key in argv or list(BUILDERS):
        p, _ = BUILDERS[key]()
        print("built", p.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
