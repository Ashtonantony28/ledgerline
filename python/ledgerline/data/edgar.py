"""SEC EDGAR XBRL fetcher with an on-disk cache.

SEC's fair-access policy asks automated clients to send a descriptive User-Agent with a
contact and to stay under 10 requests per second. Set LEDGERLINE_UA to your own
"Name contact@domain" string; the default is a generic client name.

Raw downloads go to data/raw/ and are never committed (CLAUDE.md, data rule). The
normalised snapshot that a model version uses is committed under fixtures/ together with
the SHA-256 of the raw file it came from.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RAW_DIR = REPO / "data" / "raw"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DEFAULT_UA = "Ledgerline financial-modelling research client"
MIN_INTERVAL_S = 0.15  # stays well under SEC's 10 requests/second limit

# Companies used by the models. CIKs from EDGAR company search.
CIKS: dict[str, int] = {
    "COST": 909832,
    "WMT": 104169,
    "TGT": 27419,
    "BJ": 1531152,
    "DG": 29534,
    "KR": 56873,
    "HD": 354950,
    "LOW": 60667,
    "SKX": 1065837,
}

_last_request = 0.0


def _user_agent() -> str:
    return os.environ.get("LEDGERLINE_UA", DEFAULT_UA)


def raw_path(ticker: str) -> Path:
    return RAW_DIR / f"{ticker.upper()}.json"


def fetch_companyfacts(ticker: str, refresh: bool = False) -> dict:
    """Return the companyfacts JSON for `ticker`, downloading it if not cached."""
    global _last_request
    path = raw_path(ticker)
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    cik = CIKS[ticker.upper()]
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(COMPANYFACTS_URL.format(cik=cik), headers={"User-Agent": _user_agent()})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    _last_request = time.monotonic()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return json.loads(body)


def sha256_of(ticker: str) -> str:
    return hashlib.sha256(raw_path(ticker).read_bytes()).hexdigest()
