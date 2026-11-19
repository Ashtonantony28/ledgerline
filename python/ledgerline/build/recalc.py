"""Headless recalculation and read-back of generated workbooks (ADR 0005).

openpyxl writes formulas without cached values. LibreOffice (headless) opens the file,
recalculates every formula and saves a copy whose cells carry values, which openpyxl can
then read with data_only=True. Before a release the same check runs in real Excel on
Windows via xlwings (tools/excel_check.py) to catch engine differences.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from openpyxl import load_workbook

SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


def recalc(path: Path, out_dir: Path | None = None) -> Path:
    if not SOFFICE:
        raise RuntimeError("LibreOffice (soffice) not found; install it to recalculate workbooks")
    path = Path(path)
    out_dir = Path(out_dir or tempfile.mkdtemp(prefix="ledgerline-recalc-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="lo-profile-"))  # isolated profile: parallel-safe
    cmd = [SOFFICE, f"-env:UserInstallation=file://{profile}", "--headless", "--calc",
           "--convert-to", "xlsx:Calc Office Open XML", "--outdir", str(out_dir), str(path)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    shutil.rmtree(profile, ignore_errors=True)
    out = out_dir / path.with_suffix(".xlsx").name
    if not out.exists():
        raise RuntimeError(f"LibreOffice produced no output for {path}")
    return out


class Values:
    """Read recalculated values by (sheet, row key, column index) using the build layout."""

    def __init__(self, recalculated: Path, layout: dict | Path):
        if not isinstance(layout, dict):
            layout = json.loads(Path(layout).read_text())
        self.layout = layout
        self.wb = load_workbook(recalculated, data_only=True)

    def series(self, sheet: str, key: str) -> list:
        r = self.layout["sheets"][sheet][key]
        ws = self.wb[sheet]
        return [ws[f"{c}{r}"].value for c in self.layout["timeline"]["cols"]]

    def fcst(self, sheet: str, key: str) -> list:
        return self.series(sheet, key)[self.layout["timeline"]["n_hist"]:]

    def hist(self, sheet: str, key: str) -> list:
        return self.series(sheet, key)[: self.layout["timeline"]["n_hist"]]

    def const(self, sheet: str, key: str):
        r = self.layout["sheets"][sheet][key]
        return self.wb[sheet][f"C{r}"].value

    def errors(self) -> list[str]:
        bad = []
        for ws in self.wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("#") and c.value.rstrip("!?0/").upper() in (
                            "#REF", "#NAME", "#VALUE", "#DIV", "#N/A", "#NUM", "#NULL") or (
                            isinstance(c.value, str) and c.value in ("#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NUM!", "Err:502", "Err:522", "Err:523")):
                        bad.append(f"{ws.title}!{c.coordinate}={c.value}")
        return bad


class FormulasValues(Values):
    """Second calculation engine: the pure-Python `formulas` package (supports circularity).

    Used to cross-check LibreOffice and as the CI engine for circular (average-balance) mode,
    which LibreOffice's headless iteration does not converge on (docs/known-differences.md).
    """

    def __init__(self, path: Path, layout: dict | Path, circular: bool = True):
        import formulas  # imported lazily: heavy

        if not isinstance(layout, dict):
            layout = json.loads(Path(layout).read_text())
        self.layout = layout
        path = Path(path)
        model = formulas.ExcelModel().loads(str(path)).finish(circular=circular)
        sol = model.calculate()
        self._book = path.name.upper()
        self._vals: dict[str, object] = {}
        for k, v in sol.items():
            key = k.upper().replace("'", "")
            try:
                val = v.value[0, 0] if hasattr(v, "value") else v
            except Exception:  # ranges
                continue
            self._vals[key] = val.item() if hasattr(val, "item") else val

    def _get(self, sheet: str, ref: str):
        v = self._vals.get(f"[{self._book}]{sheet.upper()}!{ref}")
        if v is None or (isinstance(v, str) and v == ""):
            return None
        if type(v).__name__ in ("XlError",):
            return str(v)
        return v

    def series(self, sheet: str, key: str) -> list:
        r = self.layout["sheets"][sheet][key]
        return [self._get(sheet, f"{c}{r}") for c in self.layout["timeline"]["cols"]]

    def const(self, sheet: str, key: str):
        return self._get(sheet, f"C{self.layout['sheets'][sheet][key]}")

    def errors(self) -> list[str]:
        return [f"{k}={v}" for k, v in self._vals.items() if k != "CIRCULAR" and (
                type(v).__name__ in ("XlError", "XlCircular") or (isinstance(v, str) and v[:1] == "#" and len(v) > 1))]
