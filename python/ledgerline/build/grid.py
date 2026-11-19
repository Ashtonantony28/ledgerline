"""Declarative time-series sheet builder (ADR 0003: hybrid generator + hand polish).

A model is a set of sheets. Time-series sheets share one timeline (historical then forecast
columns). Rows are declared with formula *templates*; the builder lays out every row first
and then renders templates, so a row can refer to rows declared later or on other sheets.

Template references (always resolved to plain A1 references, so the workbook stays a normal,
auditable Excel file with no hidden machinery):
    {key}              same sheet, same column
    {key@-1}           same sheet, previous column (any integer offset)
    {Sheet.key}        another sheet, same column (sheet names must not contain '.')
    {Sheet.key@-1}     another sheet, offset column
    {$key}             the row's constant cell (column C), absolute: $C$n
    {Sheet.$key}       constant cell on another sheet
    {key:all} / {key:hist} / {key:fcst}   the row's whole time range (absolute row)
    {key#k} / {Sheet.key#k}               fixed timeline column k (0-based), absolute: $J$12
    {col}              the current column letter

Layout (FAST-style): column A label, B unit, C constant/total, D spacer, E.. timeline.
Rows 4-7 carry the timeline: period end, fiscal-year label, forecast flag, forecast year #.
Styles: input (blue), calc (black), link (green), total (bold, top border), check (red when non-zero).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

FIRST_TIME_COL = 5          # column E
CONST_COL = 3               # column C
FIRST_DATA_ROW = 9
TIMELINE_ROWS = {"period_end": 4, "fy": 5, "is_fcst": 6, "fcst_n": 7}

FMT = {
    "m": '#,##0;(#,##0);"–"',
    "m1": '#,##0.0;(#,##0.0);"–"',
    "pct": '0.0%;(0.0%);"–"',
    "x": '0.00"x";(0.00"x");"–"',
    "ps": '#,##0.00;(#,##0.00);"–"',
    "n": '#,##0;(#,##0);"–"',
    "n1": '#,##0.0;(#,##0.0);"–"',
    "days": '0.0;(0.0);"–"',
    "flag": '0;-0;"–"',
    "date": "yyyy-mm-dd",
    "text": "@",
}
BLUE, BLACK, GREEN, RED, GREY = "0000FF", "000000", "008000", "C00000", "808080"
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
FCST_FILL = PatternFill("solid", fgColor="F2F2F2")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN_TOP = Border(top=Side(style="thin"))

_REF = re.compile(r"\{([^{}]+)\}")


@dataclass
class Timeline:
    period_ends: list[str]   # ISO dates (forecast ends estimated)
    labels: list[str]        # e.g. FY2026
    n_hist: int

    @property
    def n(self) -> int:
        return len(self.labels)

    def col(self, i: int) -> str:
        return get_column_letter(FIRST_TIME_COL + i)

    def is_fcst(self, i: int) -> bool:
        return i >= self.n_hist


@dataclass
class Row:
    key: str | None
    label: str
    unit: str = ""
    hist: object = None       # template str, list of values, or callable(i)->value/template
    fcst: object = None
    const: object = None      # value or template for column C
    style: str = "calc"       # input | calc | link | total | check | header | section | blank | text
    fmt: str = "m"
    note: str | None = None   # cell comment on the label (sources, rationale)
    const_note: str | None = None
    cell_notes: dict[int, str] = field(default_factory=dict)


class Sheet:
    def __init__(self, model: "Model", name: str, title: str, timeline: bool = True, units: str = "$m unless stated"):
        self.model, self.name, self.title, self.has_timeline, self.units = model, name, title, timeline, units
        self.rows: list[Row] = []
        self.row_of: dict[str, int] = {}
        self.free: list[tuple[str, object, dict]] = []  # free-form cells for non-timeline sheets
        self.col_widths: dict[str, float] = {}

    # --- declaration -------------------------------------------------------------------
    def add(self, key: str | None, label: str, unit: str = "", hist=None, fcst=None, all=None,
            const=None, style: str = "calc", fmt: str = "m", note: str | None = None,
            const_note: str | None = None) -> Row:
        if all is not None:
            hist = fcst = all
        r = Row(key, label, unit, hist, fcst, const, style, fmt, note, const_note)
        self.rows.append(r)
        if key:
            if key in self.row_of or key in TIMELINE_ROWS:
                raise ValueError(f"duplicate row key {self.name}.{key}")
            self.row_of[key] = FIRST_DATA_ROW + len(self.rows) - 1
        return r

    def section(self, text: str) -> None:
        self.add(None, text, style="section")

    def blank(self) -> None:
        self.add(None, "", style="blank")

    def cell(self, ref: str, value, **style) -> None:
        """Free-form cell (for Cover/Log/text sheets or one-off labels)."""
        self.free.append((ref, value, style))

    def ref(self, key: str, absolute: bool = True) -> str:
        """A1 address of a row's constant cell, for use from other sheets."""
        r = self.row(key)
        return f"'{self.name}'!$C${r}" if absolute else f"'{self.name}'!C{r}"

    def row(self, key: str) -> int:
        if key in TIMELINE_ROWS:
            return TIMELINE_ROWS[key]
        try:
            return self.row_of[key]
        except KeyError:
            raise KeyError(f"no row {key!r} on sheet {self.name!r}") from None


class Model:
    def __init__(self, timeline: Timeline, title: str):
        self.timeline, self.title = timeline, title
        self.sheets: dict[str, Sheet] = {}
        self.names: dict[str, str] = {}  # defined names -> A1 refs
        self.iterate = False

    def sheet(self, name: str, title: str, timeline: bool = True, **kw) -> Sheet:
        s = Sheet(self, name, title, timeline, **kw)
        self.sheets[name] = s
        return s

    # --- template rendering ------------------------------------------------------------
    def render(self, sheet: Sheet, tmpl: str, i: int | None) -> str:
        tl = self.timeline

        def sub(m: re.Match) -> str:
            tok = m.group(1)
            if tok == "col":
                return tl.col(i)
            sh, rest = (tok.split(".", 1) if "." in tok else (None, tok))
            target = self.sheets[sh] if sh else sheet
            prefix = f"'{target.name}'!" if target is not sheet else ""
            if rest.startswith("$"):
                return f"{prefix}$C${target.row(rest[1:])}"
            if "#" in rest:  # fixed timeline column, absolute: {key#4}
                key, k = rest.split("#")
                return f"{prefix}${tl.col(int(k))}${target.row(key)}"
            if ":" in rest:
                key, span = rest.split(":")
                r = target.row(key)
                lo, hi = {"all": (0, tl.n - 1), "hist": (0, tl.n_hist - 1), "fcst": (tl.n_hist, tl.n - 1)}[span]
                return f"{prefix}${tl.col(lo)}${r}:${tl.col(hi)}${r}"
            off = 0
            if "@" in rest:
                rest, o = rest.split("@")
                off = int(o)
            if i is None:
                raise ValueError(f"time reference {tok!r} in a constant cell on {sheet.name}")
            j = i + off
            if not 0 <= j < tl.n:
                raise ValueError(f"{sheet.name}: reference {tok!r} falls off the timeline at column {i}")
            return f"{prefix}{tl.col(j)}{target.row(rest)}"

        return _REF.sub(sub, tmpl)

    def _value(self, sheet: Sheet, spec, i: int | None):
        if spec is None:
            return None
        if callable(spec):
            spec = spec(i)
        if isinstance(spec, (list, tuple)):
            spec = spec[i if i is not None else 0]
            if callable(spec):
                spec = spec(i)
        if isinstance(spec, str) and spec.startswith("="):
            return self.render(sheet, spec, i)
        return spec

    # --- output ------------------------------------------------------------------------
    def save(self, path) -> dict:
        wb = Workbook()
        wb.remove(wb.active)
        tl = self.timeline
        layout: dict = {"timeline": {"labels": tl.labels, "n_hist": tl.n_hist,
                                     "cols": [tl.col(i) for i in range(tl.n)]}, "sheets": {}}
        for sheet in self.sheets.values():
            ws = wb.create_sheet(sheet.name)
            ws.sheet_view.showGridLines = False
            ws["A1"] = sheet.title
            ws["A1"].font = Font(bold=True, size=14, color="1F3864")
            ws["A2"] = sheet.units if sheet.has_timeline else None
            ws["A2"].font = Font(italic=True, color=GREY)
            if sheet.has_timeline:
                self._write_timeline(ws)
                for idx, row in enumerate(sheet.rows):
                    self._write_row(ws, sheet, row, FIRST_DATA_ROW + idx)
                ws.column_dimensions["A"].width = 46
                ws.column_dimensions["B"].width = 9
                ws.column_dimensions["C"].width = 12
                ws.column_dimensions["D"].width = 2
                for i in range(tl.n):
                    ws.column_dimensions[tl.col(i)].width = 11
                ws.freeze_panes = f"{tl.col(0)}{FIRST_DATA_ROW}"
                ws.page_setup.orientation = "landscape"
                ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.print_title_cols = "A:C"
            for ref, value, st in sheet.free:
                c = ws[ref]
                c.value = self.render(sheet, value, None) if isinstance(value, str) and value.startswith("=") else value
                _apply_free_style(c, st)
            for col, w in sheet.col_widths.items():
                ws.column_dimensions[col].width = w
            layout["sheets"][sheet.name] = dict(sheet.row_of)
        for name, fn in getattr(self, "charts", []):
            fn(wb[name])
        for name, ref in self.names.items():
            from openpyxl.workbook.defined_name import DefinedName
            wb.defined_names[name] = DefinedName(name, attr_text=ref)
        wb.calculation = CalcProperties(fullCalcOnLoad=True, iterate=self.iterate, iterateCount=200,
                                        iterateDelta=1e-9)
        wb.save(path)
        return layout

    def _write_timeline(self, ws) -> None:
        tl = self.timeline
        labels = {"period_end": "Period end", "fy": "Fiscal year", "is_fcst": "Forecast flag (1 = forecast)",
                  "fcst_n": "Forecast year #"}
        for key, r in TIMELINE_ROWS.items():
            ws.cell(r, 1, labels[key]).font = Font(color=GREY, italic=True)
            for i in range(tl.n):
                c = ws.cell(r, FIRST_TIME_COL + i)
                if key == "period_end":
                    c.value = tl.period_ends[i]
                elif key == "fy":
                    c.value = tl.labels[i]
                    c.font = Font(bold=True, color="FFFFFF")
                    c.fill = HEADER_FILL
                elif key == "is_fcst":
                    c.value = 1 if tl.is_fcst(i) else 0
                else:
                    c.value = i - tl.n_hist + 1 if tl.is_fcst(i) else 0
                c.alignment = Alignment(horizontal="right")
                if key != "fy":
                    c.font = Font(color=GREY)

    def _write_row(self, ws, sheet: Sheet, row: Row, r: int) -> None:
        tl = self.timeline
        a = ws.cell(r, 1, row.label)
        if row.style == "section":
            a.font = Font(bold=True, color="1F3864", size=11)
            return
        if row.style in ("blank",):
            return
        if row.note:
            a.comment = Comment(row.note, "Ledgerline")
        ws.cell(r, 2, row.unit).font = Font(color=GREY)
        if row.style == "total":
            a.font = Font(bold=True)
        if row.const is not None:
            c = ws.cell(r, CONST_COL, self._value(sheet, row.const, None))
            _style_cell(c, "input" if not (isinstance(c.value, str) and str(c.value).startswith("=")) else row.style, row.fmt)
            if row.const_note:
                c.comment = Comment(row.const_note, "Ledgerline")
        for i in range(tl.n):
            spec = row.fcst if tl.is_fcst(i) else row.hist
            v = self._value(sheet, spec, i)
            if v is None:
                continue
            c = ws.cell(r, FIRST_TIME_COL + i, v)
            style = row.style
            if not (isinstance(v, str) and v.startswith("=")) and style != "check":
                style = "input"  # every literal number is an input, whatever the row's style
            if style == "calc" and isinstance(v, str) and "!" in v and _is_pure_link(v):
                style = "link"
            _style_cell(c, style, row.fmt)
            if tl.is_fcst(i) and style not in ("input",):
                c.fill = FCST_FILL
            if row.style == "check":
                ws.conditional_formatting.add(c.coordinate, CellIsRule(operator="notBetween", formula=["-0.001", "0.001"],
                                                                       font=Font(color=RED, bold=True)))


def _is_pure_link(f: str) -> bool:
    return re.fullmatch(r"=('[^']+'|[A-Za-z0-9_]+)!\$?[A-Z]+\$?\d+", f) is not None


def _style_cell(c, style: str, fmt: str) -> None:
    c.number_format = FMT.get(fmt, fmt)
    if style == "input":
        c.font = Font(color=BLUE)
        c.fill = INPUT_FILL
    elif style == "link":
        c.font = Font(color=GREEN)
    elif style == "total":
        c.font = Font(bold=True)
        c.border = THIN_TOP
    elif style == "check":
        c.font = Font(color=GREY)
    else:
        c.font = Font(color=BLACK)


def _apply_free_style(c, st: dict) -> None:
    if not st:
        return
    font_kw = {k: st[k] for k in ("bold", "size", "italic") if k in st}
    if "color" in st:
        font_kw["color"] = st["color"]
    if font_kw:
        c.font = Font(**font_kw)
    if "fmt" in st:
        c.number_format = FMT.get(st["fmt"], st["fmt"])
    if st.get("input"):
        c.font = Font(color=BLUE, bold=st.get("bold", False))
        c.fill = INPUT_FILL
    if st.get("wrap"):
        c.alignment = Alignment(wrap_text=True, vertical="top")
    if "note" in st:
        c.comment = Comment(st["note"], "Ledgerline")
    if "fill" in st:
        c.fill = PatternFill("solid", fgColor=st["fill"])
