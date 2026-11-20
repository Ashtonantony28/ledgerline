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
    if "CircSwitch" in m.names:
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


LBO_SHEETS = [
    ("Inputs", "Transaction terms from the merger information statement (sourced), judgement, rate paths"),
    ("Hist", "Skechers 10-K history (blue, sourced per cell)"),
    ("Scenarios", "Base / upside / downside operating paths"), ("Drivers", "Live operating drivers"),
    ("Transaction", "Sources and uses, entry multiple, leverage at close"),
    ("Operating", "Operating model to levered free cash flow"),
    ("Debt", "Tranches, revolver, cash sweep, PIK accrual, interest, covenants"),
    ("Returns", "Exit value, IRR, MOIC, value-creation bridge"),
    ("Sensitivity", "IRR grids: offer price x exit multiple, exit year x exit multiple"),
    ("Checks", "Integrity checks and master flag"),
]


def build_03(scenario: int = 1, out: Path | None = None) -> tuple[Path, dict]:
    from ..models.lbo import add_lbo, timeline
    from ..models.lbo_inputs import build_lbo_inputs
    inp = build_lbo_inputs(scenario)
    m = Model(timeline(inp), "SKX LBO")
    add_lbo(m, inp)
    add_cover(m, "Skechers U.S.A.: LBO back-test (3G Capital take-private, 2025)", inp, LBO_SHEETS)
    add_log(m, [(date.today().isoformat(), "Generated from spec/SKX_LBO.yaml and fixtures/SKX (M4).")])
    _reorder(m, ["Cover"] + [n for n, _ in LBO_SHEETS])
    path = Path(out or OUT / "03_SKX_LBO.xlsx")
    layout = m.save(path)
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


MNA_SHEETS = [
    ("Inputs", "Switches, merger terms and PPA inputs from the proxy statement/prospectus (sourced), judgement"),
    ("Hist_DKS", "DICK'S 10-K history (blue, sourced per cell)"), ("Hist_FL", "Foot Locker 10-K history (blue, sourced per cell)"),
    ("Scenarios", "Operating cases, Foot Locker management projections, consideration structures"),
    ("Drivers", "Live drivers"), ("Transaction", "Consideration, sources and uses, purchase price allocation, valuation"),
    ("Standalone", "Standalone forecasts for both companies"),
    ("ProForma", "Adjustments, pro forma EPS, accretion / dilution, breakeven synergies, credit, contribution"),
    ("Sensitivity", "Accretion grids: offer price x stock mix, year x synergy realisation"),
    ("Checks", "Integrity checks and master flag"),
]


def build_04(scenario: int = 1, structure: int = 3, out: Path | None = None) -> tuple[Path, dict]:
    from ..models.mna import add_mna, timeline
    from ..models.mna_inputs import build_mna_inputs
    inp = build_mna_inputs(scenario, structure)
    m = Model(timeline(inp), "DKS FL M&A")
    add_mna(m, inp)
    add_cover(m, "DICK'S Sporting Goods / Foot Locker: accretion-dilution back-test (2025)", inp, MNA_SHEETS)
    m.sheets["Cover"].cell("A11", "Consideration mix")
    m.sheets["Cover"].cell("B11", "='Inputs'!C%d" % m.sheets["Inputs"].row("structure_name"), bold=True)
    add_log(m, [(date.today().isoformat(), "Generated from spec/DKS_FL_MA.yaml and fixtures/DKS, fixtures/FL (M5).")])
    _reorder(m, ["Cover"] + [n for n, _ in MNA_SHEETS])
    path = Path(out or OUT / "04_DKS_FL_MnA.xlsx")
    layout = m.save(path)
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


GROUP_SHEETS = [
    ("Inputs", "Close calendar inputs: FX rates, ownership, prepaids, accruals, bank statement"),
    ("CoA", "Chart of accounts with statement mapping"),
    ("Opening", "Opening trial balances by entity (local currency)"),
    ("TB_Unadj", "Unadjusted closing trial balances (local currency, seeded synthetic ledger)"),
    ("Schedules", "Depreciation and tax provision"),
    ("Journals", "Month-end close journals J1-J7"),
    ("TB_Adj", "Adjusted trial balances = unadjusted + journals"),
    ("Translation", "S2 GBP to USD at current rate, CTA plug and roll-forward"),
    ("Elims", "Consolidation eliminations E1-E12 (intercompany, investment, NCI)"),
    ("Consol", "Consolidation worksheet: entities, eliminations, group"),
    ("Statements", "Group income statement, balance sheet and equity roll-forward"),
    ("CashFlow", "Indirect cash flow statement from trial-balance movements"),
    ("Recs", "Bank and intercompany reconciliations"),
    ("Checks", "Integrity checks and master flag"),
    ("Checklist", "Close checklist with owners and sign-off (VBA stamps sign-off in Excel)"),
]


def build_05(out: Path | None = None) -> tuple[Path, dict]:
    from ..data.group import load
    from ..models.group import add_group
    from .grid import Timeline
    g = load()
    m = Model(Timeline([], [], 0), "Group close")
    addr = add_group(m, g)
    c = m.sheet("Cover", "Ledgerline Group: month-end close and consolidation (synthetic)", timeline=False)
    c.col_widths = {"A": 34, "B": 80}
    c.cell("A3", "Entities"); c.cell("B3", "P (US parent), S1 (US), S2 (UK, GBP), S3 (US, 80% owned)", bold=True)
    c.cell("A4", "Units"); c.cell("B4", "$ millions; S2 ledgers in GBP millions until translated")
    c.cell("A5", "Data"); c.cell("B5", "Seeded synthetic ledgers (python/ledgerline/data/group.py, seed fixed); no real company")
    c.cell("A6", "Framework"); c.cell("B6", "US GAAP: ASC 810 consolidation, ASC 830 translation, full-goodwill NCI")
    c.cell("A9", "Model integrity")
    c.cell("B9", "=IF(MasterCheck=0,\"ALL CHECKS PASS\",\"CHECK FAILURE - see Checks sheet\")", bold=True)
    c.cell("A10", "Built"); c.cell("B10", f"{date.today().isoformat()} by the Ledgerline generator (see Log)")
    c.cell("A12", "Colour code", bold=True)
    c.cell("A13", "Blue on yellow", input=True); c.cell("B13", "Hard-coded input (ledger data or close input)")
    c.cell("A14", "Black", color="000000"); c.cell("B14", "Formula")
    c.cell("A15", "Green", color="008000"); c.cell("B15", "Direct link to another sheet")
    c.cell("A18", "Sheets", bold=True)
    for k, (name, desc) in enumerate(GROUP_SHEETS):
        c.cell(f"A{19 + k}", name, bold=True); c.cell(f"B{19 + k}", desc)
    r = 20 + len(GROUP_SHEETS)
    c.cell(f"A{r}", "Disclaimer", bold=True); c.cell(f"B{r}", DISCLAIMER, wrap=True)
    add_log(m, [(date.today().isoformat(), "Generated from fixtures/group (seeded synthetic ledgers) (M6).")])
    _reorder(m, ["Cover"] + [n for n, _ in GROUP_SHEETS])
    path = Path(out or OUT / "05_Group_Close.xlsx")
    layout = m.save(path)
    layout["addr"] = {k: list(v) for k, v in addr.items()}
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


FPA_SHEETS = [
    ("Inputs", "Forecast case switch, FY2025 anchors from workbook 05, budget and forecast assumptions, hiring plan"),
    ("Actuals", "Monthly GL export Jan-Sep 2026 (seeded synthetic ledger) with GL control-total ties"),
    ("Scenarios", "Rolling-forecast cases: volume growth, price change, net hires"),
    ("Drivers", "Live drivers: actual months from the GL, forecast months from run-rates and the live case"),
    ("Budget", "FY2026 driver-based budget by product and department"),
    ("PnL", "Outlook P&L, free cash flow and cash, lowest forecast cash and headroom"),
    ("Variance", "Budget vs actual and outlook; price / volume / mix / cost / headcount bridges"),
    ("Accuracy", "June forecast against actuals: MAPE, bias, change in outlook"),
    ("Dashboard", "Headline numbers and charts"),
    ("Checks", "Integrity checks and master flag"),
]


def build_06(scenario: int = 1, out: Path | None = None) -> tuple[Path, dict]:
    from ..data.fpa import load
    from ..models.fpa import add_fpa, add_dashboard, add_charts, timeline
    g = load()
    m = Model(timeline(g), "FP&A")
    add_fpa(m, g, scenario)
    add_dashboard(m)
    c = m.sheet("Cover", "Ledgerline Group: FY2026 budget, 9+3 rolling forecast and variance analysis (synthetic)", timeline=False)
    c.col_widths = {"A": 34, "B": 80}
    c.cell("A3", "Company"); c.cell("B3", "Ledgerline Group (synthetic; the consolidated group of workbook 05)", bold=True)
    c.cell("A4", "Units"); c.cell("B4", "$ millions; volumes in millions of units; headcount in people")
    c.cell("A5", "Actuals"); c.cell("B5", f"{m.timeline.labels[0]} to {m.timeline.labels[m.timeline.n_hist - 1]} (GL export)")
    c.cell("A6", "Rolling forecast"); c.cell("B6", f"{m.timeline.labels[m.timeline.n_hist]} to {m.timeline.labels[-1]}")
    c.cell("A7", "Live forecast case"); c.cell("B7", "='Inputs'!C%d" % m.sheets["Inputs"].row("scenario_name"), bold=True)
    c.cell("A9", "Model integrity")
    c.cell("B9", "=IF(MasterCheck=0,\"ALL CHECKS PASS\",\"CHECK FAILURE - see Checks sheet\")", bold=True)
    c.cell("A10", "Built"); c.cell("B10", f"{date.today().isoformat()} by the Ledgerline generator (see Log)")
    c.cell("A12", "Colour code", bold=True)
    c.cell("A13", "Blue on yellow", input=True); c.cell("B13", "Hard-coded input (every one carries a source note)")
    c.cell("A14", "Black", color="000000"); c.cell("B14", "Formula")
    c.cell("A15", "Green", color="008000"); c.cell("B15", "Direct link to another sheet")
    c.cell("A16", "Grey shading"); c.cell("B16", "Forecast months")
    c.cell("A18", "Sheets", bold=True)
    for k, (name, desc) in enumerate(FPA_SHEETS):
        c.cell(f"A{19 + k}", name, bold=True); c.cell(f"B{19 + k}", desc)
    r = 20 + len(FPA_SHEETS)
    c.cell(f"A{r}", "Disclaimer", bold=True); c.cell(f"B{r}", DISCLAIMER, wrap=True)
    add_log(m, [(date.today().isoformat(), "Generated from spec/FPA.yaml and fixtures/fpa (seeded synthetic GL) (M7).")])
    _reorder(m, ["Cover"] + [n for n, _ in FPA_SHEETS])
    path = Path(out or OUT / "06_FPA_Forecast.xlsx")
    layout = m.save(path)
    add_charts(path, m, g["spec"]["calendar"]["budget_months"])
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


LAB_SHEETS = THREE_STATEMENT_SHEETS[:2] + [("Scenarios", THREE_STATEMENT_SHEETS[2][1]),
              ("Lab", "Scenario manager: stress-case selector and manual driver shifts feeding the whole model")] + \
    [x for x in VALUATION_SHEETS[3:-1]] + [
    ("Tornado", "One-step-down / one-step-up price for each driver, ranked by swing"),
    ("Spider", "Price as each driver moves -2 to +2 steps"),
    ("MonteCarlo", "10,000 seeded simultaneous-shift trials: percentiles, probability above market, histogram"),
    ("Checks", "Integrity checks (including live-vs-reference ties) and master flag"),
]


def build_07(stress: int = 0, manual: dict | None = None, trials: int | None = None, out: Path | None = None) -> tuple[Path, dict]:
    from dataclasses import replace
    from ..models.lab import add_lab
    from ..models.three_statement import add_three_statement, timeline
    from ..models.valuation import add_valuation, valuation_checks
    from ..models.valuation_inputs import build_val_inputs
    from ..ref.lab import run as lab_run
    inp = build_inputs("COST", scenario=1, circ=0)
    v = build_val_inputs(inp)
    lab = lab_run(inp, v, trials=trials)  # results at zero shift: the lab describes the base case
    inp = replace(inp, lab=True)
    m = Model(timeline(inp), "COST scenario lab")
    add_lab(m, lab, stress, manual)
    add_three_statement(m, inp, extra_checks=valuation_checks() + m.lab_checks)
    add_valuation(m, inp, v)
    add_cover(m, f"{inp.history.entity}: scenario and sensitivity lab (tornado, spider, stress, Monte Carlo)", inp, LAB_SHEETS)
    m.sheets["Cover"].cell("A11", "Live stress case")
    m.sheets["Cover"].cell("B11", "='Lab'!C%d" % m.sheets["Lab"].row("stress_name"), bold=True)
    add_log(m, [(date.today().isoformat(), "Generated from spec/COST.yaml, spec/LAB_COST.yaml, fixtures/COST, fixtures/market.json (M8).")])
    _reorder(m, ["Cover"] + [n for n, _ in LAB_SHEETS])
    path = Path(out or OUT / "07_COST_ScenarioLab.xlsx")
    layout = m.save(path)
    path.with_suffix(".layout.json").write_text(json.dumps(layout, indent=1) + "\n")
    return path, layout


BUILDERS = {"00": build_00, "01": build_01, "02": build_02, "03": build_03, "04": build_04, "05": build_05, "06": build_06,
            "07": build_07}


def main(argv: list[str]) -> int:
    for key in argv or list(BUILDERS):
        p, _ = BUILDERS[key]()
        print("built", p.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
