"""Market inputs for the cost of capital, snapshot to fixtures/market.json (reviewed change on refresh).

    python -m ledgerline.data.market COST

  risk-free rate   FRED DGS10 (10-year Treasury constant maturity), latest observation
  equity premium   Damodaran implied ERP by month (ERPbymonth.xlsx, "T12m with sustainable payout")
  beta             OLS of 60 monthly total-price returns of the stock on the S&P 500 (Yahoo Finance)
  52-week range    Yahoo Finance daily highs/lows over the last year (football field)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import edgar

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
ERP_URL = "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range={r}&interval={i}"
OUT = edgar.REPO / "fixtures" / "market.json"
UA = {"User-Agent": "Mozilla/5.0"}


def _get(url: str, headers: dict | None = None) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or UA), timeout=60) as r:
        return r.read()


def risk_free() -> dict:
    rows = [r for r in csv.reader(io.StringIO(_get(FRED, {"User-Agent": "curl/8.5.0"}).decode())) if len(r) == 2 and r[1] not in ("", ".", "DGS10")]
    d, v = rows[-1]
    return {"value": float(v) / 100, "date": d, "source": "FRED DGS10 (10-year Treasury constant maturity)"}


def erp() -> dict:
    from openpyxl import load_workbook
    tmp = Path(tempfile.mkdtemp()) / "erp.xlsx"
    tmp.write_bytes(_get(ERP_URL))
    ws = load_workbook(tmp, data_only=True)["Historical ERP"]
    rows = [r for r in ws.iter_rows(values_only=True) if isinstance(r[0], datetime) and r[8] is not None]
    last = rows[-1]
    return {"value": float(last[8]), "date": last[0].date().isoformat(),
            "source": "Damodaran implied ERP by month, ERPbymonth.xlsx, column 'ERP (T12 m with sustainable payout)'"}


def _monthly_closes(t: str) -> dict[str, float]:
    res = json.loads(_get(CHART.format(t=urllib.parse.quote(t), r="6y", i="1mo")))["chart"]["result"][0]
    closes = res["indicators"]["adjclose"][0]["adjclose"] if "adjclose" in res["indicators"] else res["indicators"]["quote"][0]["close"]
    out = {}
    for ts, c in zip(res["timestamp"], closes):
        if c is not None:
            out[datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")] = float(c)
    return out


def beta(ticker: str, months: int = 60) -> dict:
    s, m = _monthly_closes(ticker), _monthly_closes("^GSPC")
    keys = sorted(set(s) & set(m))[:-1][-(months + 1):]  # drop the partial current month
    rs = [s[b] / s[a] - 1 for a, b in zip(keys, keys[1:])]
    rm = [m[b] / m[a] - 1 for a, b in zip(keys, keys[1:])]
    n = len(rs)
    ms, mm = sum(rs) / n, sum(rm) / n
    cov = sum((x - ms) * (y - mm) for x, y in zip(rs, rm)) / (n - 1)
    var = sum((y - mm) ** 2 for y in rm) / (n - 1)
    return {"value": cov / var, "n_months": n, "window": f"{keys[0]}..{keys[-1]}",
            "source": f"OLS beta of {n} monthly adjusted-close returns of {ticker} on ^GSPC (Yahoo Finance)"}


def range_52w(ticker: str) -> dict:
    res = json.loads(_get(CHART.format(t=ticker, r="1y", i="1d")))["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    hi = max(x for x in q["high"] if x is not None)
    lo = min(x for x in q["low"] if x is not None)
    return {"high": round(hi, 2), "low": round(lo, 2), "source": "Yahoo Finance daily high/low, trailing 1 year"}


def main(argv: list[str]) -> int:
    tickers = [a.upper() for a in argv] or ["COST"]
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    data["risk_free"] = risk_free()
    data["erp"] = erp()
    data["snapshot"] = datetime.now(timezone.utc).date().isoformat()
    for t in tickers:
        data.setdefault("tickers", {})[t] = {"beta": beta(t), "range_52w": range_52w(t)}
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
