"""Export selected sheets of each workbook to PDF through LibreOffice UNO (run with the system python3 that has `uno`).

    python3 tools/book_uno.py spec.json        # spec: [{"src": "...xlsx", "pdf": "...pdf", "sheets": [...]}, ...]

Called by `python -m ledgerline.book`; kept separate because the UNO bridge lives in LibreOffice's Python, not the
project's. The workbook is recalculated after loading, every other sheet is hidden, and charts are kept.
"""
import json
import subprocess
import sys
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def main(spec_path):
    jobs = json.load(open(spec_path))
    port = 2002
    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", "--nologo",
                             f"--accept=socket,host=127.0.0.1,port={port};urp;"])
    ctx = None
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            ctx = resolver.resolve(f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    try:
        for job in jobs:
            doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(job["src"]), "_blank", 0, (prop("Hidden", True),))
            doc.calculateAll()
            sheets = doc.Sheets
            keep = set(job["sheets"])
            for name in sheets.ElementNames:
                if name not in keep:
                    sheets.getByName(name).IsVisible = False
            doc.storeToURL(uno.systemPathToFileUrl(job["pdf"]), (prop("FilterName", "calc_pdf_Export"),))
            doc.close(True)
    finally:
        try:
            desktop.terminate()
        except Exception:
            pass
        proc.wait(timeout=30)


if __name__ == "__main__":
    main(sys.argv[1])
