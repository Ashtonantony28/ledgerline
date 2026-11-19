"""Workbook 00: the Data workbook. Normalised 10-K history per company, with live tie-out formulas.

One sheet per company: line items x fiscal years (blue, as filed or plug, source note per cell),
followed by tie-out rows written as formulas so the identities can be seen holding in Excel,
and a short ratio block. A Summary sheet lists each company's tie-out status.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

from ..build.grid import BLUE, FMT, HEADER_FILL, INPUT_FILL, GREY
from ..data.history import load
from ..data.normalise import load_tagmap

M = 1e6
STMT_TITLE = {"income_statement": "Income statement", "balance_sheet": "Balance sheet", "cash_flow": "Cash flow",
              "operating_kpis": "Operating KPIs"}
UNIT_FREE = {"eps_diluted", "stores"}

TIEOUTS = [  # label, formula over row refs {key}
    ("Assets - (liabilities + equity)", "={total_assets}-{total_liabilities}-{total_equity}"),
    ("Reported L&E - assets", "={total_le}-{total_assets}"),
    ("Net income - (total - NCI)", "={net_income}-({net_income_total}-{nci_income})"),
    ("CFO + CFI + CFF + FX - change in cash", "={cfo}+{cfi}+{cff}+{fx_effect}-{net_change_cash}"),
    ("Revenue - COGS - SG&A - other - EBIT", "={revenue}-{cogs}-{sga}-{other_opex}-{operating_income}"),
    ("Current assets build - reported", "={cash}+{st_investments}+{receivables}+{inventory}+{other_current_assets}-{total_current_assets}"),
]
RATIOS = [
    ("Revenue growth", "={revenue}/{revenue@-1}-1", "pct", 1),
    ("Gross margin", "=1-{cogs}/{revenue}", "pct", 0),
    ("EBIT margin", "={operating_income}/{revenue}", "pct", 0),
    ("Net margin", "={net_income}/{revenue}", "pct", 0),
    ("EBITDA ($m)", "={operating_income}+{da}", "m", 0),
    ("Net debt ($m)", "={short_term_debt}+{current_debt}+{lt_debt}-{cash}-{st_investments}", "m", 0),
    ("Capex % revenue", "=-{capex}/{revenue}", "pct", 0),
    ("Effective tax rate", "={income_tax}/{pretax_income}", "pct", 0),
]


def _company_sheet(wb: Workbook, ticker: str) -> tuple[str, int]:
    h = load(ticker)
    ws = wb.create_sheet(ticker)
    ws.sheet_view.showGridLines = False
    ws["A1"] = f"{h.entity} ({ticker}): normalised 10-K history"
    ws["A1"].font = Font(bold=True, size=14, color="1F3864")
    ws["A2"] = "$m unless stated (shares in millions; EPS in $; warehouses/stores as counts)"
    ws["A2"].font = Font(italic=True, color=GREY)
    labels = h.fy_labels()
    ws.cell(4, 1, "Period end").font = Font(italic=True, color=GREY)
    ws.cell(5, 1, "Fiscal year").font = Font(italic=True, color=GREY)
    for j, (lab, end) in enumerate(zip(labels, h.period_ends)):
        ws.cell(4, 3 + j, end.isoformat()).font = Font(color=GREY)
        c = ws.cell(5, 3 + j, lab)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
    row = 7
    row_of: dict[str, int] = {}
    current = None
    for stmt, key in h.items:
        if stmt != current:
            ws.cell(row, 1, STMT_TITLE[stmt]).font = Font(bold=True, color="1F3864")
            row += 1
            current = stmt
        ws.cell(row, 1, key.replace("_", " "))
        scale = 1 if key in UNIT_FREE else M
        for j, v in enumerate(h.values[key]):
            c = ws.cell(row, 3 + j, v / scale)
            c.font = Font(color=BLUE)
            c.fill = INPUT_FILL
            c.number_format = FMT["ps"] if key == "eps_diluted" else FMT["m"]
            c.comment = Comment(h.source[key][j], "Ledgerline")
        row_of[key] = row
        row += 1
    row += 1

    def render(tmpl: str, j: int) -> str:
        import re

        def sub(m):
            k, _, off = m.group(1).partition("@")
            return f"{get_column_letter(3 + j + (int(off) if off else 0))}{row_of[k]}"
        return re.sub(r"\{([a-z_@\-0-9]+)\}", sub, tmpl)

    ws.cell(row, 1, "Tie-out (every cell must be zero)").font = Font(bold=True, color="1F3864")
    row += 1
    first_tie = row
    for label, tmpl in TIEOUTS:
        ws.cell(row, 1, label)
        for j in range(len(labels)):
            c = ws.cell(row, 3 + j, render(tmpl, j))
            c.number_format = FMT["m1"]
        row += 1
    last_tie = row - 1
    row += 1
    ws.cell(row, 1, "Ratios").font = Font(bold=True, color="1F3864")
    row += 1
    for label, tmpl, fmt, first in RATIOS:
        ws.cell(row, 1, label)
        for j in range(first, len(labels)):
            c = ws.cell(row, 3 + j, render(tmpl, j))
            c.number_format = FMT[fmt]
        row += 1
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 2
    for j in range(len(labels)):
        ws.column_dimensions[get_column_letter(3 + j)].width = 11
    ws.freeze_panes = "C6"
    rng = f"$C${first_tie}:${get_column_letter(2 + len(labels))}${last_tie}"
    return rng, len(labels)


def build_00(tickers: list[str], out: Path) -> Path:
    wb = Workbook()
    summ = wb.active
    summ.title = "Summary"
    summ["A1"] = "Ledgerline Data workbook: normalised SEC 10-K history"
    summ["A1"].font = Font(bold=True, size=14, color="1F3864")
    summ["A2"] = (f"Built {date.today().isoformat()} from fixtures/<TICKER>/ (SEC EDGAR XBRL companyfacts). "
                  "Each blue cell's comment names the US-GAAP tag and filing accession it came from.")
    summ["F4"], summ["G4"] = "Tie-out tolerance ($m)", 0.5
    summ["G4"].font = Font(color=BLUE)
    summ["G4"].fill = INPUT_FILL
    summ["G4"].comment = Comment("Filings are reported in $ millions; half a million covers rounding (ADR 0004).", "Ledgerline")
    summ["A4"], summ["B4"], summ["C4"], summ["D4"] = "Ticker", "Years", "Tie-out (max abs, $m)", "Status"
    for c in "ABCD":
        summ[f"{c}4"].font = Font(bold=True)
    for k, t in enumerate(tickers):
        rng, n = _company_sheet(wb, t)
        r = 5 + k
        summ[f"A{r}"] = t
        summ[f"B{r}"] = n
        summ[f"B{r}"].font = Font(color=BLUE)
        summ[f"C{r}"] = f"=MAX(ABS(MAX('{t}'!{rng})),ABS(MIN('{t}'!{rng})))"
        summ[f"C{r}"].number_format = "0.0"
        summ[f"D{r}"] = f'=IF(C{r}<=$G$4,"TIES","CHECK")'
    summ.column_dimensions["A"].width = 12
    summ.column_dimensions["C"].width = 22
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(out)
    return out
