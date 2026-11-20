"""Seeded error injection: prove the checks catch real modelling errors (plan §4.3, M10 target >= 95%).

    python -m ledgerline.audit.mutation 01 --n 40 --seed 7     # workbook 01 (three-statement)
    python -m ledgerline.audit.mutation 04 --n 40 --seed 7     # workbook 04 (M&A)
    python -m ledgerline.audit.mutation 05 --n 40 --seed 7     # workbook 05 (group close, free-form sheets)

Each mutant breaks one thing in a built workbook, the way people break spreadsheets:
  hardcode   overwrite one forecast formula with its current value (a "paste values")
  wrongrow   point one cell's reference at the row below
  wholesign  flip + and - in every forecast formula of a row (consistent, so the audit can't see it)
  wholelag   shift every same-sheet reference in a row's forecast one column left
  input      nudge one scenario input by 1%
A mutant is caught when the audit raises a high finding, the master check fails, or the
recalculated outputs differ from the Python reference. A mutant whose recalculated outputs
are identical to the original is *equivalent* (it changed nothing observable) and is excluded.
"""
from __future__ import annotations

import json
import random
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from ..build.recalc import Values, recalc
from .audit import REF_RE, audit

KINDS = ("hardcode", "wrongrow", "wholesign", "wholelag", "input")


def _target(workbook: str) -> dict:
    """Builder, calculation sheets, reference outputs and reference values for a workbook."""
    from ..build.workbooks import build_01, build_04
    from ..verify import MNA_OUTPUTS, THREE_STATEMENT_OUTPUTS
    if workbook == "01":
        from ..models.assumptions import build_inputs
        from ..ref.three_statement import run as ref_run
        return dict(build=lambda p: build_01("COST", out=p), calc=("Schedules", "IS", "BS", "CF", "Drivers"),
                    outputs=THREE_STATEMENT_OUTPUTS, ref=lambda: ref_run(build_inputs("COST")))
    if workbook == "04":
        from ..models.mna_inputs import build_mna_inputs
        from ..ref.mna import run as ref_run
        return dict(build=lambda p: build_04(1, 3, out=p), calc=("Standalone", "ProForma", "Drivers"),
                    outputs=MNA_OUTPUTS, ref=lambda: ref_run(build_mna_inputs(1, 3)))
    raise ValueError(f"no mutation target for workbook {workbook}")


@dataclass
class Result:
    kind: str
    where: str
    caught: bool
    equivalent: bool
    how: str


def _fcst_formula_cells(ws, layout):
    cols = layout["timeline"]["cols"][layout["timeline"]["n_hist"]:]
    out = []
    for r in layout["sheets"][ws.title].values():
        for c in cols:
            v = ws[f"{c}{r}"].value
            if isinstance(v, str) and v.startswith("="):
                out.append((r, c))
    return out


def mutate(src: Path, dst: Path, layout: dict, kind: str, rng: random.Random, base_values: Values,
           calc_sheets: tuple[str, ...]) -> str:
    wb = load_workbook(src)
    if kind == "input":
        ws = wb["Scenarios"]
        rows = [r for k, r in layout["sheets"]["Scenarios"].items() if k.endswith("_base")]  # live case
        cols = layout["timeline"]["cols"][layout["timeline"]["n_hist"]:]
        cells = [(r, c) for r in rows for c in cols if isinstance(ws[f"{c}{r}"].value, (int, float))]
        r, c = rng.choice(cells)
        ws[f"{c}{r}"].value = ws[f"{c}{r}"].value * 1.01 + 1e-4
        wb.save(dst)
        return f"Scenarios!{c}{r}"
    ws = wb[rng.choice(calc_sheets)]
    cells = _fcst_formula_cells(ws, layout)
    r, c = rng.choice(cells)
    where = f"{ws.title}!{c}{r}"
    cols = layout["timeline"]["cols"][layout["timeline"]["n_hist"]:]
    before = {col: ws[f"{col}{r}"].value for col in cols}
    if kind == "hardcode":
        val = base_values.wb[ws.title][f"{c}{r}"].value
        ws[f"{c}{r}"].value = val if isinstance(val, (int, float)) else 0
    elif kind == "wrongrow":
        f = ws[f"{c}{r}"].value
        ws[f"{c}{r}"].value = REF_RE.sub(lambda m: f"{m.group(1) or ''}{m.group(2)}{m.group(3)}{m.group(4)}{int(m.group(5)) + 1}", f, count=1)
    elif kind == "wholesign":
        for col in cols:
            f = ws[f"{col}{r}"].value
            if isinstance(f, str) and f.startswith("="):
                ws[f"{col}{r}"].value = "=" + f[1:].translate(str.maketrans("+-", "-+"))
        where = f"{ws.title}!row {r}"
    elif kind == "wholelag":
        allcols = layout["timeline"]["cols"]
        for col in cols:
            f = ws[f"{col}{r}"].value
            if isinstance(f, str) and f.startswith("="):
                def lag(m):
                    if m.group(1) or m.group(2) or m.group(3) not in allcols:
                        return m.group(0)
                    j = allcols.index(m.group(3))
                    return f"{allcols[max(j - 1, 0)]}{m.group(4)}{m.group(5)}"
                ws[f"{col}{r}"].value = REF_RE.sub(lag, f)
        where = f"{ws.title}!row {r}"
    if all(ws[f"{col}{r}"].value == before[col] for col in before):
        return None  # mutation changed nothing (e.g. no +/- to flip); caller re-picks
    wb.save(dst)
    return where


def run(workbook: str = "01", n: int = 40, seed: int = 7) -> list[Result]:
    from ..verify import compare

    tg = _target(workbook)
    outputs = tg["outputs"]
    tmp = Path(tempfile.mkdtemp(prefix="ledgerline-mut-"))
    src, layout = tg["build"](tmp / "orig.xlsx")
    base_rc = recalc(src, tmp / "orig_rc")
    base = Values(base_rc, layout)
    ref = tg["ref"]()
    base_out = {(s, k): base.fcst(s, k) for s, k, _, _ in outputs}
    rng = random.Random(seed)
    results = []
    for i in range(n):
        kind = KINDS[i % len(KINDS)]
        dst = tmp / f"m{i}.xlsx"
        where = None
        while where is None:
            where = mutate(src, dst, layout, kind, rng, base, tg["calc"])
        rc = recalc(dst, tmp / f"m{i}_rc")
        v = Values(rc, layout)
        out = {(s, k): v.fcst(s, k) for s, k, _, _ in outputs}
        master = v.const("Checks", "master")
        equivalent = out == base_out and master == 0
        how = []
        findings, _, _ = audit(dst, rc, layout)
        if any(f.severity == "high" for f in findings):
            how.append("audit")
        if master != 0:
            how.append("checks")
        if compare(v, ref, outputs):
            how.append("reference")
        results.append(Result(kind, where, bool(how), equivalent and not how, "+".join(how)))
    return results


GROUP_CALC = ("Schedules", "Journals", "TB_Adj", "Translation", "Elims", "Consol", "Statements", "CashFlow", "Recs")
GROUP_INPUTS = ("Inputs", "TB_Unadj", "Opening")
GROUP_KINDS = ("hardcode", "wrongrow", "sign", "input")


def _mutate_free(src: Path, dst: Path, kind: str, rng: random.Random, base_wb) -> str | None:
    """One mutation on a workbook without a timeline (workbook 05): cells are picked anywhere on the sheets."""
    wb = load_workbook(src)
    if kind == "input":
        ws = wb[rng.choice(GROUP_INPUTS)]
        cells = [c for row in ws.iter_rows() for c in row
                 if isinstance(c.value, (int, float)) and not isinstance(c.value, bool) and c.value != 0 and c.column > 2]
        if not cells:
            return None
        c = rng.choice(cells)
        c.value = c.value * 1.01
        wb.save(dst)
        return f"{ws.title}!{c.coordinate}"
    ws = wb[rng.choice(GROUP_CALC)]
    cells = [c for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    if kind == "sign":
        cells = [c for c in cells if re.search(r"[A-Z]\$?\d+\s*[+-]", c.value)]
    if kind == "wrongrow":
        cells = [c for c in cells if REF_RE.search(c.value)]
    if not cells:
        return None
    c = rng.choice(cells)
    if kind == "hardcode":
        v = base_wb[ws.title][c.coordinate].value
        if not isinstance(v, (int, float)):
            return None
        c.value = v
    elif kind == "sign":
        m = re.search(r"([A-Z]\$?\d+\s*)([+-])", c.value)
        c.value = c.value[:m.start(2)] + ("-" if m.group(2) == "+" else "+") + c.value[m.end(2):]
    else:
        refs = list(re.finditer(r"(\$?[A-Z]{1,3}\$?)(\d+)(?![\d(])", c.value))
        if not refs:
            return None
        m = rng.choice(refs)
        c.value = c.value[:m.start(2)] + str(int(m.group(2)) + 1) + c.value[m.end(2):]
    wb.save(dst)
    return f"{ws.title}!{c.coordinate}"


def run_group(n: int = 40, seed: int = 7) -> list[Result]:
    from ..build.workbooks import build_05
    from ..data.group import load
    from ..ref.group import run as ref_run
    from ..verify import group_compare, group_expected
    tmp = Path(tempfile.mkdtemp(prefix="ledgerline-mut05-"))
    src, layout = build_05(out=tmp / "orig.xlsx")
    addr = layout["addr"]
    base_wb = load_workbook(recalc(src, tmp / "orig_rc"), data_only=True)
    snap = lambda wb: {k: wb[s][c].value for k, (s, c) in addr.items()}
    base = snap(base_wb)
    exp = group_expected(ref_run(load()))
    rng = random.Random(seed)
    results = []
    for i in range(n):
        kind = GROUP_KINDS[i % len(GROUP_KINDS)]
        dst = tmp / f"m{i}.xlsx"
        where = None
        while where is None:
            where = _mutate_free(src, dst, kind, rng, base_wb)
        rc = recalc(dst, tmp / f"m{i}_rc")
        wb = load_workbook(rc, data_only=True)
        out = snap(wb)
        how = []
        findings, _, _ = audit(dst, rc, layout)
        if any(f.severity == "high" for f in findings):
            how.append("audit")
        if out["master"] != 0:
            how.append("checks")
        if group_compare(lambda s_, c_: wb[s_][c_].value, addr, exp):
            how.append("reference")
        equivalent = out == base and not how
        results.append(Result(kind, where, bool(how), equivalent, "+".join(how)))
    return results


def summary(results: list[Result], workbook: str = "01") -> str:
    live = [r for r in results if not r.equivalent]
    caught = sum(r.caught for r in live)
    lines = [f"# Mutation test (workbook {workbook})", "",
             f"Mutants: {len(results)}, equivalent (no observable change): {len(results) - len(live)}, "
             f"caught: {caught}/{len(live)} = {caught / max(len(live), 1):.1%}", "",
             "| kind | where | caught by |", "|---|---|---|"]
    lines += [f"| {r.kind} | {r.where} | {'equivalent' if r.equivalent else (r.how or '**MISSED**')} |" for r in results]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    n = int(argv[argv.index("--n") + 1]) if "--n" in argv else 40
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 7
    wbs = [a for a in argv if a.isdigit() and len(a) == 2 and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in ("--n", "--seed"))]
    workbook = wbs[0] if wbs else "01"
    res = run_group(n, seed) if workbook == "05" else run(workbook, n, seed)
    text = summary(res, workbook)
    out = Path(__file__).resolve().parents[3] / "docs" / f"mutation-{workbook}.md"
    out.write_text(text)
    print(text.splitlines()[2])
    live = [r for r in res if not r.equivalent]
    return 0 if sum(r.caught for r in live) >= 0.95 * len(live) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
