"""Excel-native Monte Carlo for workbook 07 through xlwings (needs desktop Excel; verified at M10).

    python -m ledgerline.xl.montecarlo workbooks/07_COST_ScenarioLab.xlsx --trials 500

Draws the same seeded shifts as ledgerline.ref.lab, types each draw into the Lab sheet's manual-shift cells, lets
Excel recalculate, reads the live prices back, and reports the largest difference from the Python reference for
the same draw. This is the cross-check that the Python Monte Carlo written into the workbook is what Excel itself
would produce. It is slow by design (one full recalculation per trial); the cloud build uses the Python results.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    import xlwings as xw  # imported here: only available where Excel is installed

    from ..models.assumptions import build_inputs
    from ..models.valuation_inputs import build_val_inputs
    from ..ref import lab

    path = Path(argv[0])
    trials = int(argv[argv.index("--trials") + 1]) if "--trials" in argv else 200
    layout = json.loads(path.with_suffix(".layout.json").read_text())["sheets"]["Lab"]
    inp = build_inputs("COST")
    v = build_val_inputs(inp)
    sp = lab.spec()
    sp["monte_carlo"]["trials"] = trials
    draws = lab.montecarlo(inp, v, sp)
    book = xw.Book(str(path))
    ws = book.sheets["Lab"]
    ws.range(f"C{layout['stress']}").value = 0
    worst = 0.0
    try:
        for k, sh in enumerate(draws["draws"]):
            for key, x in sh.items():
                ws.range(f"C{layout['man_' + key]}").value = x
            book.app.calculate()
            g = ws.range(f"C{layout['live_price_g']}").value
            worst = max(worst, abs(g - draws["gordon"][k]))
    finally:
        for key in sp["drivers"]:
            ws.range(f"C{layout['man_' + key]}").value = 0
        book.app.calculate()
    print(f"{trials} trials; largest |Excel - Python| = {worst:.2e} $/share")
    return 0 if worst < 1e-6 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
