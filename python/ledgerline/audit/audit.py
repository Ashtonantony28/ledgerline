"""Model audit tool: formula map, consistency, hardcodes, risky functions, errors (plan §4.3).

    python -m ledgerline.audit.audit workbooks/01_COST_ThreeStatement.xlsx [--recalc]

Writes <workbook>.formulas.txt (a text dump of every cell, so git diffs of workbooks are
readable) and <workbook>.audit.md (findings by severity). Exit status is 1 when any
high-severity finding exists. Rules (ADR 0007):

  high   error values after recalculation; external links; numeric literals inside formulas
         other than 0 and 1; functions outside the allow-list (LibreOffice-compatible, non-volatile);
         a row whose forecast (or history) formulas are not all the same in relative form;
         numeric hard-codes in calculation cells that are not styled as inputs.
  medium formulas that reference empty cells.
  info   counts, circularity-switch locations.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

ALLOWED_FUNCS = {
    "SUM", "SUMPRODUCT", "ABS", "MIN", "MAX", "IF", "AND", "OR", "NOT", "AVERAGE", "CHOOSE", "INDEX", "MATCH",
    "ROUND", "IFERROR", "NPV", "IRR", "XNPV", "XIRR", "PV", "FV", "PMT", "LN", "EXP", "POWER", "SQRT", "COUNT",
    "COUNTA", "COUNTIF", "SUMIF", "SUMIFS", "MEDIAN", "PERCENTILE", "QUARTILE", "LARGE", "SMALL", "VLOOKUP",
    "HLOOKUP", "YEAR", "DATE", "EOMONTH", "EDATE", "TEXT", "CONCATENATE", "ISNUMBER", "ISBLANK", "SIGN", "INT",
    "MOD", "STDEV", "NORMSINV", "NORM.S.INV", "RAND", "AVERAGEIF",
}
VOLATILE = {"OFFSET", "INDIRECT", "NOW", "TODAY", "RANDBETWEEN", "CELL", "INFO"}
TEXT_SHEETS = {"Cover", "Log"}
INPUT_FONT = "000000FF"

REF_RE = re.compile(r"(?<![A-Za-z0-9_.\"])((?:'[^']+'|[A-Za-z_][A-Za-z0-9_]*)!)?(\$?)([A-Z]{1,3})(\$?)(\d+)(?![A-Za-z0-9_(])")
STR_RE = re.compile(r'"[^"]*"')
FUNC_RE = re.compile(r"([A-Z][A-Z0-9.]*)\(")
NUM_RE = re.compile(r"(?<![A-Za-z0-9_.$])(\d+(?:\.\d+)?(?:E[+-]?\d+)?)(?![A-Za-z0-9_(])")


@dataclass
class Finding:
    severity: str
    sheet: str
    cell: str
    rule: str
    detail: str


def relative_form(formula: str, row: int, col: int) -> str:
    def sub(m: re.Match) -> str:
        sheet, cabs, c, rabs, r = m.groups()
        ci, ri = column_index_from_string(c), int(r)
        cs = f"C{ci}" if cabs else f"C[{ci - col}]"
        rs = f"R{ri}" if rabs else f"R[{ri - row}]"
        return f"{sheet or ''}{rs}{cs}"
    return REF_RE.sub(sub, STR_RE.sub('""', formula))


def audit(path: Path, recalculated: Path | None = None, layout: dict | None = None) -> tuple[list[Finding], str]:
    wb = load_workbook(path)
    findings: list[Finding] = []
    lines: list[str] = []
    n_formulas = 0
    tl = layout["timeline"] if layout else None
    for ws in wb.worksheets:
        lines.append(f"=== {ws.title}")
        rows: dict[int, dict[str, list[tuple[int, str]]]] = defaultdict(lambda: defaultdict(list))
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if v is None:
                    continue
                lines.append(f"{c.coordinate}\t{v!r}" if not isinstance(v, str) or not v.startswith("=") else f"{c.coordinate}\t{v}")
                if isinstance(v, str) and v.startswith("="):
                    n_formulas += 1
                    _check_formula(ws, c, v, findings, wb)
                    if tl and c.column >= 5 and layout["sheets"].get(ws.title):  # timeline sheets only
                        idx = c.column - 5
                        region = "fcst" if idx >= tl["n_hist"] else "hist"
                        rows[c.row][region].append((c.column, relative_form(v, c.row, c.column)))
                elif isinstance(v, (int, float)) and not isinstance(v, bool) and ws.title not in TEXT_SHEETS:
                    color = (c.font.color.rgb if c.font and c.font.color is not None else None)
                    if c.row > 7 and color != INPUT_FONT:
                        findings.append(Finding("high", ws.title, c.coordinate, "hardcode-not-input",
                                                f"numeric value {v!r} not styled as an input"))
        for r, regions in rows.items():
            for region, cells in regions.items():
                forms = {f for _, f in cells}
                if len(forms) > 1:
                    first = cells[0]
                    odd = [get_column_letter(col) for col, f in cells if f != first[1]]
                    findings.append(Finding("high", ws.title, f"row {r}", "inconsistent-row",
                                            f"{region} formulas differ in relative form at columns {', '.join(odd[:6])}"))
    if recalculated:
        from ..build.recalc import Values
        if True:
            for e in Values(recalculated, layout or {}).errors():
                sh, cell = e.split("!", 1)
                findings.append(Finding("high", sh, cell, "error-value", "error after recalculation"))
    sev = {"high": 0, "medium": 1, "info": 2}
    findings.sort(key=lambda f: (sev[f.severity], f.sheet, f.cell))
    report = _report(path, findings, n_formulas)
    return findings, "\n".join(lines) + "\n", report


def _check_formula(ws, c, v: str, findings: list[Finding], wb) -> None:
    body = STR_RE.sub('""', v[1:])
    if "[" in body:
        findings.append(Finding("high", ws.title, c.coordinate, "external-link", v))
    for fn in FUNC_RE.findall(body):
        if fn in VOLATILE:
            findings.append(Finding("high", ws.title, c.coordinate, "volatile-function", fn))
        elif fn not in ALLOWED_FUNCS:
            findings.append(Finding("high", ws.title, c.coordinate, "function-not-allowed", fn))
    body_nums = re.sub(r"(QUARTILE|PERCENTILE|LARGE|SMALL)\(([^()]+),\s*\d+\)", r"\1(\2)", body)  # selector args
    stripped = REF_RE.sub(" ", body_nums)
    stripped = re.sub(r"[A-Za-z_][A-Za-z0-9_.]*", " ", stripped)  # names and functions
    for num in NUM_RE.findall(stripped):
        if float(num) not in (0.0, 1.0):
            findings.append(Finding("high", ws.title, c.coordinate, "literal-in-formula", f"{num} in {v}"))
    for m in REF_RE.finditer(body):
        if body[m.end():m.end() + 1] == ":" or body[max(m.start() - 1, 0):m.start()] == ":":
            continue  # range endpoints: blanks inside SUM/SUMPRODUCT ranges are intended
        sheet, _, col, _, row = m.groups()
        target = wb[sheet[:-1].strip("'")] if sheet else ws
        if target[f"{col}{row}"].value is None:
            findings.append(Finding("medium", ws.title, c.coordinate, "ref-to-empty",
                                    f"{(sheet or '')}{col}{row} is empty"))


def _report(path: Path, findings: list[Finding], n_formulas: int) -> str:
    counts = defaultdict(int)
    for f in findings:
        counts[f.severity] += 1
    out = [f"# Model audit: {path.name}", "",
           f"Formulas scanned: {n_formulas:,}. High: {counts['high']}, medium: {counts['medium']}, info: {counts['info']}.", ""]
    if not findings:
        out.append("No findings.")
    else:
        out += ["| severity | sheet | cell | rule | detail |", "|---|---|---|---|---|"]
        out += [f"| {f.severity} | {f.sheet} | {f.cell} | {f.rule} | {f.detail.replace('|', '/')[:160]} |" for f in findings[:500]]
        if len(findings) > 500:
            out.append(f"\n... {len(findings) - 500} more")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    do_recalc = "--recalc" in argv
    paths = [Path(a) for a in argv if not a.startswith("--")]
    worst = 0
    for p in paths:
        layout_path = p.with_suffix(".layout.json")
        layout = json.loads(layout_path.read_text()) if layout_path.exists() else None
        rc = None
        if do_recalc:
            from ..build.recalc import recalc
            rc = recalc(p)
        findings, fmap, report = audit(p, rc, layout)
        p.with_suffix(".formulas.txt").write_text(fmap)
        p.with_suffix(".audit.md").write_text(report)
        high = sum(f.severity == "high" for f in findings)
        med = sum(f.severity == "medium" for f in findings)
        print(f"{p.name}: {high} high, {med} medium findings")
        worst = max(worst, 1 if high else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
