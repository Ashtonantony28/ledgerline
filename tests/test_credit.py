"""M9: workbook 09 (credit) matches ref/credit.py on both engines; interface exports meet their contracts.

Verify: pytest -q tests/test_credit.py
"""
import csv
import math

import pytest

from ledgerline import exports
from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_09
from ledgerline.ref import credit
from ledgerline.verify import close

NUM = [("Credit", k) for k in ("ebitda", "interest", "adj_debt", "net_debt", "fcf", "leverage", "net_leverage", "coverage",
                               "ebit_coverage", "fcf_debt", "cfo_debt", "z", "lev_band", "cov_band", "idx", "pd", "lev_cushion",
                               "cov_cushion", "cushion", "cap_leverage", "cap_coverage", "capacity")] + \
      [("Stress", k) for k in ("s_ebitda", "s_interest", "s_leverage", "s_coverage", "s_z", "s_idx", "s_pd", "notches", "s_breach")]
TEXT = [("Credit", "rating"), ("Credit", "zone"), ("Stress", "s_rating")]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("credit")
    path, layout = build_09(out=d / "09.xlsx")
    return path, layout, recalc(path, d / "rc"), credit.run()["results"]


def _compare(v, ref):
    bad = []
    for sheet, key in NUM:
        for j, (a, x) in enumerate(zip(v.series(sheet, key), ref)):
            if not close(a, x[key], "ratio"):
                bad.append(f"{sheet}.{key}[{x['ticker']}] {a} vs {x[key]}")
    for sheet, key in TEXT:
        for a, x in zip(v.series(sheet, key), ref):
            if a != x[key]:
                bad.append(f"{sheet}.{key}[{x['ticker']}] {a} vs {x[key]}")
    return bad


def test_libreoffice_matches_reference(built):
    path, layout, rc, ref = built
    v = Values(rc, layout)
    assert not v.errors() and v.const("Checks", "master") == 0
    assert not (bad := _compare(v, ref)), bad[:20]


def test_formulas_engine_matches_reference(built):
    path, layout, _, ref = built
    assert not (bad := _compare(FormulasValues(path, layout), ref)), bad[:20]


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report


def test_rating_rounding_matches_excel():
    assert credit.round_half_up(2.5) == 3 and credit.round_half_up(3.49) == 3


def _read(name):
    with open(exports.OUT / name) as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("name,cols", [
    ("borrower_spreads.csv", [c[0] for c in exports.SPREAD_COLUMNS]),
    ("borrower_spreads_history.csv", [c[0] for c in exports.SPREAD_COLUMNS if c[0] not in exports.HISTORY_DROP]),
    ("pd_table.csv", [c[0] for c in exports.PD_COLUMNS]),
    ("fundamental_signals.csv", [c[0] for c in exports.SIGNAL_COLUMNS])])
def test_export_contract(name, cols):
    rows = _read(name)
    assert rows and list(rows[0]) == cols
    assert {r["schema_version"] for r in rows} == {exports.SCHEMA_VERSION}


def test_exports_are_current(tmp_path):
    """Committed exports equal a fresh run (a stale export fails CI, like a stale fixture)."""
    for p in exports.write(tmp_path):
        assert p.read_text() == (exports.OUT / p.name).read_text(), p.name


def test_borrower_spreads_tie_to_reference():
    ref = {x["ticker"]: x for x in credit.run()["results"]}
    for r in _read("borrower_spreads.csv"):
        x = ref[r["ticker"]]
        assert math.isclose(float(r["leverage"]), x["leverage"], rel_tol=1e-9) and r["rating"] == x["rating"]


def test_signals_are_point_in_time_dated():
    for r in _read("fundamental_signals.csv"):
        assert r["available_from"] > r["fy_end"]


def test_history_latest_rows_equal_snapshot():
    """The long file's latest year per borrower is the snapshot row (same ratios, same rating)."""
    snap = {r["ticker"]: r for r in _read("borrower_spreads.csv")}
    last = {}
    for r in _read("borrower_spreads_history.csv"):
        last[r["ticker"]] = r
    for t, r in last.items():
        assert r["fy_end"] == snap[t]["fy_end"] and r["leverage"] == snap[t]["leverage"] and r["rating"] == snap[t]["rating"]


def test_pd_table_matches_spec_and_rises():
    pds = [float(r["pd_1y"]) for r in _read("pd_table.csv")]
    assert pds == credit.spec()["scorecard"]["pd_1y"] and pds == sorted(pds)
