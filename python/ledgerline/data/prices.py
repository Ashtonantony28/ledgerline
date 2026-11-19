"""End-of-day price snapshot for market-based inputs (comps, buyback share count).

    python -m ledgerline.data.prices COST WMT ...

Writes fixtures/prices.csv (ticker, date, close, source). The snapshot date is recorded so
the models are reproducible; refreshing prices is a reviewed change like any fixture.
Source: Yahoo Finance public chart endpoint (free, unofficial). Shares outstanding come from
the dei:EntityCommonStockSharesOutstanding cover-page fact in the latest 10-K/10-Q.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone

from . import edgar

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=10d&interval=1d"
PRICES = edgar.REPO / "fixtures" / "prices.csv"


def fetch_close(ticker: str) -> tuple[str, float]:
    req = urllib.request.Request(CHART_URL.format(t=ticker), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())["chart"]["result"][0]
    pairs = [(ts, c) for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    ts, close = pairs[-1]
    day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    return day, round(float(close), 2)


def shares_outstanding(ticker: str) -> tuple[float, str]:
    """Latest cover-page shares outstanding (dei), with its as-of date."""
    facts = edgar.fetch_companyfacts(ticker)
    node = facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
    latest = max(node, key=lambda f: (f["end"], f["filed"]))
    return float(latest["val"]), f"dei:EntityCommonStockSharesOutstanding@{latest['accn']} as of {latest['end']}"


def load() -> dict[str, dict]:
    with open(PRICES) as f:
        return {r["ticker"]: {**r, "close": float(r["close"]), "shares_out": float(r["shares_out"])}
                for r in csv.DictReader(f)}


def main(argv: list[str]) -> int:
    tickers = [a.upper() for a in argv] or list(edgar.CIKS)
    rows = load() if PRICES.exists() else {}
    for t in tickers:
        day, close = fetch_close(t)
        so, so_src = shares_outstanding(t)
        rows[t] = {"ticker": t, "date": day, "close": close, "source": "Yahoo Finance daily close",
                   "shares_out": so, "shares_source": so_src}
        print(t, day, close, f"{so/1e6:,.1f}m shares")
    with open(PRICES, "w", newline="") as f:
        w = csv.DictWriter(f, ["ticker", "date", "close", "source", "shares_out", "shares_source"], lineterminator="\n")
        w.writeheader()
        for t in sorted(rows):
            w.writerow(rows[t])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
