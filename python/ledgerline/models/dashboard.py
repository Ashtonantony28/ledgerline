"""Workbook 08: one-page dashboard of the suite (docs/models/dashboard.md).

Every number is read from a recalculated delivered workbook (LibreOffice), so the dashboard shows exactly what the
workbooks show; each value's note names the workbook and cell. The integrity table carries every workbook's master
check, and this workbook's own master check fails if any of them does.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference

from ..build.grid import Model

# (section, label, workbook stem, getter, number format)
HEADLINES = [
    ("Costco three-statement (01)", "FY2027 revenue, base case ($m)", "01_COST_ThreeStatement", ("fcst", "IS", "revenue", 0), "m"),
    ("Costco three-statement (01)", "FY2027 diluted EPS ($)", "01_COST_ThreeStatement", ("fcst", "IS", "eps_diluted", 0), "ps"),
    ("Costco valuation (02)", "WACC", "02_COST_Valuation", ("const", "WACC", "wacc"), "pct"),
    ("Costco valuation (02)", "DCF price, perpetuity growth ($)", "02_COST_Valuation", ("const", "DCF", "price_g"), "ps"),
    ("Costco valuation (02)", "DCF price, exit multiple ($)", "02_COST_Valuation", ("const", "DCF", "price_x"), "ps"),
    ("Costco valuation (02)", "Market price ($)", "02_COST_Valuation", ("const", "WACC", "price"), "ps"),
    ("Costco valuation (02)", "Perpetual growth implied by the market price", "02_COST_Valuation", ("const", "DCF", "implied_g_mkt"), "pct"),
    ("Skechers LBO (03)", "Entry EV / EBITDA", "03_SKX_LBO", ("const", "Transaction", "entry_mult"), "x"),
    ("Skechers LBO (03)", "Leverage at close", "03_SKX_LBO", ("const", "Transaction", "leverage_close"), "x"),
    ("Skechers LBO (03)", "Sponsor IRR", "03_SKX_LBO", ("const", "Returns", "irr"), "pct"),
    ("Skechers LBO (03)", "Sponsor MOIC", "03_SKX_LBO", ("const", "Returns", "moic"), "x"),
    ("DICK'S / Foot Locker (04)", "Consideration ($m)", "04_DKS_FL_MnA", ("const", "Transaction", "consideration"), "m"),
    ("DICK'S / Foot Locker (04)", "Goodwill ($m)", "04_DKS_FL_MnA", ("const", "Transaction", "goodwill"), "m"),
    ("DICK'S / Foot Locker (04)", "Adjusted EPS accretion, FY2025", "04_DKS_FL_MnA", ("fcst", "ProForma", "acc_adj", 0), "pct"),
    ("DICK'S / Foot Locker (04)", "Adjusted EPS accretion, FY2026", "04_DKS_FL_MnA", ("fcst", "ProForma", "acc_adj", 1), "pct"),
    ("DICK'S / Foot Locker (04)", "Foot Locker net income needed to break even, FY2026 ($m)", "04_DKS_FL_MnA",
     ("fcst", "ProForma", "breakeven_fl_ni", 1), "m"),
    ("Group close (05)", "Net income attributable to the parent ($m)", "05_Group_Close", ("addr", "st_ni_parent"), "m1"),
    ("Group close (05)", "Total assets ($m)", "05_Group_Close", ("addr", "st_total_assets"), "m1"),
    ("Group close (05)", "Translation adjustment, S2 ($m)", "05_Group_Close", ("addr", "cta_plug"), "m1"),
    ("FP&A (06)", "FY2026 revenue: budget ($m)", "06_FPA_Forecast", ("const", "Variance", "fy_rev_budget"), "m1"),
    ("FP&A (06)", "FY2026 revenue: outlook ($m)", "06_FPA_Forecast", ("const", "Variance", "fy_rev_actual"), "m1"),
    ("FP&A (06)", "FY2026 EBITDA: budget ($m)", "06_FPA_Forecast", ("const", "Variance", "fy_ebitda_budget"), "m1"),
    ("FP&A (06)", "FY2026 EBITDA: outlook ($m)", "06_FPA_Forecast", ("const", "Variance", "fy_ebitda_actual"), "m1"),
    ("FP&A (06)", "June forecast MAPE", "06_FPA_Forecast", ("const", "Accuracy", "mape"), "pct"),
    ("FP&A (06)", "Cash headroom over policy minimum ($m)", "06_FPA_Forecast", ("const", "PnL", "headroom"), "m1"),
    ("Scenario lab (07)", "Monte Carlo median price, perpetuity growth ($)", "07_COST_ScenarioLab", ("cell", "MonteCarlo", "B12"), "ps"),
    ("Scenario lab (07)", "Monte Carlo 95th percentile ($)", "07_COST_ScenarioLab", ("cell", "MonteCarlo", "B15"), "ps"),
    ("Scenario lab (07)", "Share of trials above the market price", "07_COST_ScenarioLab", ("cell", "MonteCarlo", "B16"), "0.00%"),
    ("Credit (09)", "Costco scorecard rating", "09_Credit", ("series", "Credit", "rating", 0), "text"),
    ("Credit (09)", "Borrowers breaching covenants under stress (of 11)", "09_Credit", ("const", "Stress", "n_breach"), "n"),
]
WORKBOOKS = ["01_COST_ThreeStatement", "02_COST_Valuation", "03_SKX_LBO", "04_DKS_FL_MnA", "05_Group_Close",
             "06_FPA_Forecast", "07_COST_ScenarioLab", "09_Credit"]


def _master_ref(path: Path) -> tuple[str, str]:
    dn = load_workbook(path).defined_names["MasterCheck"]
    sheet, cell = next(dn.destinations)
    return sheet, cell.replace("$", "")


def read_values(src: Path, recalculated: Path, layouts: dict[str, dict]) -> dict:
    """{'headlines': [(section, label, value, fmt, note)], 'masters': [(stem, value, note)]} from recalculated workbooks."""
    wbs = {stem: load_workbook(recalculated / f"{stem}.xlsx", data_only=True) for stem in WORKBOOKS}
    out = {"headlines": [], "masters": []}
    for section, label, stem, g, fmt in HEADLINES:
        lay = layouts[stem]
        if g[0] == "const":
            sheet, cell = g[1], f"C{lay['sheets'][g[1]][g[2]]}"
        elif g[0] in ("fcst", "series"):
            cols = lay["timeline"]["cols"]
            j = (lay["timeline"]["n_hist"] if g[0] == "fcst" else 0) + g[3]
            sheet, cell = g[1], f"{cols[j]}{lay['sheets'][g[1]][g[2]]}"
        elif g[0] == "cell":
            sheet, cell = g[1], g[2]
        else:
            sheet, cell = lay["addr"][g[1]]
        v = wbs[stem][sheet][cell].value
        out["headlines"].append((section, label, v, fmt, f"{stem}.xlsx, {sheet}!{cell} (LibreOffice recalculation)"))
    for stem in WORKBOOKS:
        sheet, cell = _master_ref(src / f"{stem}.xlsx")
        out["masters"].append((stem, wbs[stem][sheet][cell].value, f"{stem}.xlsx, {sheet}!{cell} (MasterCheck)"))
    return out


def add_dashboard(m: Model, vals: dict) -> dict[str, str]:
    d = m.sheet("Dashboard", "Ledgerline: the suite on one page", timeline=False)
    d.col_widths = {"A": 58, "B": 16, "C": 4, "D": 34, "E": 12}
    r, cells, section = 4, {}, None
    for sec, label, v, fmt, note in vals["headlines"]:
        if sec != section:
            r += 1 if section else 0
            d.cell(f"A{r}", sec, bold=True)
            r, section = r + 1, sec
        d.cell(f"A{r}", label)
        d.cell(f"B{r}", v, input=True, fmt=fmt, note=note)
        cells[label] = f"B{r}"
        r += 1
    d.cell("D4", "Integrity: master check per workbook", bold=True)
    for k, (stem, v, note) in enumerate(vals["masters"], start=5):
        d.cell(f"D{k}", stem)
        d.cell(f"E{k}", v, input=True, fmt="flag", note=note)
    m_last = 4 + len(vals["masters"])
    d.cell(f"D{m_last + 1}", "Workbooks failing", bold=True)
    d.cell(f"E{m_last + 1}", f"=SUM(E5:E{m_last})", fmt="n", bold=True)
    # chart table: Costco value per share
    t0 = m_last + 4
    d.cell(f"D{t0}", "Costco value per share ($)", bold=True)
    rows = [("Market", "Market price ($)"), ("DCF, perpetuity growth", "DCF price, perpetuity growth ($)"),
            ("DCF, exit multiple", "DCF price, exit multiple ($)"), ("Monte Carlo median", "Monte Carlo median price, perpetuity growth ($)"),
            ("Monte Carlo 95th pct", "Monte Carlo 95th percentile ($)")]
    for k, (lab, key) in enumerate(rows, start=t0 + 1):
        d.cell(f"D{k}", lab)
        d.cell(f"E{k}", f"={cells[key]}", fmt="ps")

    def chart(ws):
        ch = BarChart()
        ch.title, ch.legend, ch.height, ch.width = "Costco: market price vs model values ($/share)", None, 7.5, 14
        ch.add_data(Reference(ws, min_col=5, min_row=t0 + 1, max_row=t0 + len(rows)), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=4, min_row=t0 + 1, max_row=t0 + len(rows)))
        ws.add_chart(ch, f"D{t0 + len(rows) + 2}")
        ws.page_setup.orientation = "landscape"  # one printed page for the model book
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    m.charts = getattr(m, "charts", []) + [("Dashboard", chart)]
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)", timeline=False)
    ck.col_widths = {"A": 50, "B": 12}
    ck.cell("A4", "Every delivered workbook passes its own master check")
    ck.cell("B4", f"='Dashboard'!E{m_last + 1}", fmt="n")
    ck.cell("A6", "MASTER CHECK (0 = all pass)", bold=True)
    ck.cell("B6", "=IF(B4=0,0,1)", fmt="flag", bold=True)
    m.names["MasterCheck"] = "'Checks'!$B$6"
    return cells
