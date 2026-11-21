"""Model book: the key sheets of every workbook in one PDF (plan M10).

    python -m ledgerline.book        # writes workbooks/Ledgerline_Model_Book.pdf

LibreOffice renders each workbook (recalculated, charts kept, other sheets hidden) through tools/book_uno.py; pypdf
joins the parts and adds bookmarks per workbook.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

REPO = Path(__file__).resolve().parents[2]
WB = REPO / "workbooks"
BOOK = [  # (workbook stem, bookmark, sheets)
    ("08_Dashboard", "Dashboard", ["Dashboard"]),
    ("01_COST_ThreeStatement", "01 Costco three-statement model", ["Cover", "IS", "BS", "CF", "Ratios", "Checks"]),
    ("02_COST_Valuation", "02 Costco valuation", ["WACC", "DCF", "Sensitivity", "Football"]),
    ("03_SKX_LBO", "03 Skechers / 3G Capital LBO", ["Cover", "Transaction", "Debt", "Returns", "Sensitivity"]),
    ("04_DKS_FL_MnA", "04 DICK'S / Foot Locker M&A", ["Cover", "Transaction", "ProForma", "Sensitivity"]),
    ("05_Group_Close", "05 Group close and consolidation", ["Cover", "Statements", "CashFlow", "Recs", "Checklist"]),
    ("06_FPA_Forecast", "06 FP&A budget and rolling forecast", ["Cover", "PnL", "Variance", "Accuracy", "Dashboard"]),
    ("07_COST_ScenarioLab", "07 Costco scenario lab", ["Lab", "Tornado", "Spider", "MonteCarlo"]),
    ("09_Credit", "09 Credit analysis", ["Cover", "Credit", "Stress"]),
]


def build(out: Path = WB / "Ledgerline_Model_Book.pdf") -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ledgerline-book-"))
    jobs = [{"src": str(WB / f"{stem}.xlsx"), "pdf": str(tmp / f"{stem}.pdf"), "sheets": sheets} for stem, _, sheets in BOOK]
    (tmp / "jobs.json").write_text(json.dumps(jobs))
    subprocess.run(["/usr/bin/python3", str(REPO / "tools" / "book_uno.py"), str(tmp / "jobs.json")], check=True, timeout=900)
    w = PdfWriter()
    for (stem, mark, _), job in zip(BOOK, jobs):
        start = len(w.pages)
        for page in PdfReader(job["pdf"]).pages:
            w.add_page(page)
        w.add_outline_item(mark, start)
    w.add_metadata({"/Title": "Ledgerline model book", "/Subject": "Educational portfolio models; not investment advice"})
    with open(out, "wb") as f:
        w.write(f)
    return out


if __name__ == "__main__":
    p = build()
    print("wrote", p.relative_to(REPO), len(PdfReader(p).pages), "pages")
    sys.exit(0)
