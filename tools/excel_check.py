"""Desktop Excel cross-check of the delivered workbooks (M10; ADR 0005 tolerances).

Two halves, because the cloud has LibreOffice and no Excel, and the Windows machine has Excel and no LibreOffice:

  cloud:    python tools/excel_check.py dump      # LibreOffice values of every formula cell -> workbooks/excel_check/
  Windows:  python tools/excel_check.py excel     # recalculates each workbook in Excel, compares, writes the report

The Excel half opens each workbook read-only, forces a full recalculation, reads every formula cell and compares it
with the LibreOffice value: numbers within max($0.005, 1e-9 relative), text and booleans equal. It never saves a
workbook. It also opens the circuit-breaker variant of 01 (circ = 1, iterative calculation, ADR 0006), which
LibreOffice cannot check, and reports its master check. The report goes to docs/excel-check.md.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import platform
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WB = REPO / "workbooks"
OUT = WB / "excel_check"
LO_JSON = OUT / "lo_values.json.gz"
STEMS = ["00_Data", "01_COST_ThreeStatement", "02_COST_Valuation", "03_SKX_LBO", "04_DKS_FL_MnA", "05_Group_Close",
         "06_FPA_Forecast", "07_COST_ScenarioLab", "09_Credit", "08_Dashboard"]
CIRC = "01_COST_ThreeStatement_circ"
ABS_TOL, REL_TOL = 0.005, 1e-9


def _norm(v):
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (dt.datetime, dt.date)):
        return None  # dates are compared through the formulas that use them
    return str(v)


def dump() -> None:
    """Cloud half: LibreOffice-recalculated value of every formula cell, plus the circ = 1 variant of 01."""
    sys.path.insert(0, str(REPO / "python"))
    from openpyxl import load_workbook

    from ledgerline.build.recalc import recalc
    from ledgerline.build.workbooks import build_01

    OUT.mkdir(parents=True, exist_ok=True)
    build_01(circ=1, out=OUT / f"{CIRC}.xlsx")
    data = {}
    for stem in STEMS:
        src = WB / f"{stem}.xlsx"
        f = load_workbook(src)
        v = load_workbook(recalc(src), data_only=True)
        cells = {}
        for ws in f.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        cells[f"{ws.title}!{c.coordinate}"] = _norm(v[ws.title][c.coordinate].value)
        dn = f.defined_names.get("MasterCheck")
        data[stem] = {"cells": cells, "master": next(dn.destinations) if dn else None}
        print(f"{stem}: {len(cells)} formula cells")
    with gzip.open(LO_JSON, "wt") as fh:
        json.dump(data, fh, sort_keys=True)


def _close(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))
    if a in (None, "") and b in (None, ""):
        return True
    return a == b


def excel() -> int:
    """Windows half: recalculate in Excel and compare with the LibreOffice values."""
    import xlwings as xw

    from openpyxl.utils import get_column_letter

    lo = json.loads(gzip.open(LO_JSON, "rt").read())
    app = xw.App(visible=False, add_book=False)
    app.display_alerts, app.screen_updating = False, False
    lines = [f"# Desktop Excel check\n", f"Excel {app.version} on {platform.platform()}, {dt.date.today().isoformat()}.",
             f"Tolerance: numbers within max(${ABS_TOL}, {REL_TOL:g} relative); text equal. Workbooks opened "
             "read-only and never saved.\n", "| Workbook | Formula cells | Compared | Differ | Largest difference | "
             "Master check (Excel) |", "|---|---|---|---|---|---|"]
    failed, details = 0, []
    try:
        for stem in STEMS + [CIRC]:
            path = (OUT if stem == CIRC else WB) / f"{stem}.xlsx"
            if stem == CIRC:
                app.api.Iteration, app.api.MaxIterations, app.api.MaxChange = True, 200, 1e-9
            book = app.books.open(str(path), read_only=True, update_links=False)
            app.api.CalculateFull()
            ref = lo.get(stem, {"cells": {}, "master": None})
            n = cmp = bad = 0
            worst = 0.0
            for ws in book.sheets:
                rng = ws.used_range
                r0, c0 = rng.row, rng.column
                forms = rng.options(ndim=2).formula
                vals = rng.options(ndim=2).value
                for i, frow in enumerate(forms):
                    for j, fm in enumerate(frow):
                        if not (isinstance(fm, str) and fm.startswith("=")):
                            continue
                        n += 1
                        key = f"{ws.name}!{get_column_letter(c0 + j)}{r0 + i}"
                        if key not in ref["cells"] or ref["cells"][key] is None and stem != CIRC:
                            continue
                        a, b = _norm(vals[i][j]), ref["cells"][key]
                        if a is None and isinstance(vals[i][j], (dt.datetime, dt.date)):
                            continue
                        cmp += 1
                        if isinstance(a, float) and isinstance(b, float):
                            worst = max(worst, abs(a - b))
                        if not _close(a, b):
                            bad += 1
                            if len(details) < 60:
                                details.append(f"- {stem} {key}: Excel {a!r}, LibreOffice {b!r} (`{fm}`)")
            master = None
            if ref["master"] or stem == CIRC:
                sheet, cell = ref["master"] or lo["01_COST_ThreeStatement"]["master"]
                master = book.sheets[sheet].range(cell.replace("$", "")).value
            book.close()
            if stem == CIRC:
                app.api.Iteration = False
                cmp, bad, worst = 0, 0, 0.0  # LibreOffice cannot iterate: master check only
            failed += bad + (1 if master not in (0, 0.0, None) else 0)
            lines.append(f"| {stem} | {n} | {cmp} | {bad} | {worst:.2e} | {master} |")
            print(lines[-1])
    finally:
        app.quit()
    lines += ["", f"**Result: {'PASS' if failed == 0 else 'FAIL'}** ({failed} problems).", ""]
    if details:
        lines += ["## Differences (first 60)", ""] + details
    (REPO / "docs" / "excel-check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "dump":
        dump()
    elif mode == "excel":
        sys.exit(excel())
    else:
        print(__doc__)
        sys.exit(2)
