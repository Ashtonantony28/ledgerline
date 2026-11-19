"""M4: workbook 03 (Skechers LBO) matches the reference on LibreOffice and `formulas`.

Verify: pytest -q tests/test_lbo.py
"""
import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_03
from ledgerline.models.lbo_inputs import build_lbo_inputs
from ledgerline.ref.lbo import run
from ledgerline.verify import close

SERIES = [("Operating", k, k, "usd") for k in ("revenue", "ebitda", "ebit", "capex", "change_nwc", "taxes", "ni_total",
                                             "nci_dist", "lfcf")] + \
         [("Debt", k, k, "usd") for k in ("int_tlu", "int_tle", "int_ssn", "int_pik", "int_rcf", "interest_total",
                                        "cash_interest", "rcf_draw", "sweep", "tlu", "tle", "pik", "rcf", "cash",
                                        "total_debt", "net_debt")] + \
         [("Debt", "lev_1l", "lev_1l", "ratio"), ("Debt", "icr", "icr", "ratio"),
          ("Returns", "exit_equity", "exit_equity", "usd"), ("Returns", "investor_equity", "investor_equity", "usd")]
CONSTS = [("Transaction", "uses", "uses", "usd"), ("Transaction", "cash0", "cash0", "usd"), ("Transaction", "E0", "E0", "usd"),
          ("Transaction", "entry_mult", "entry_mult", "ratio"), ("Transaction", "headline_mult", "headline_mult", "ratio"),
          ("Returns", "moic", "moic", "ratio"), ("Returns", "attr_ebitda", "attr_ebitda", "usd"),
          ("Returns", "attr_delever", "attr_delever", "usd"), ("Returns", "value_created", "value_created", "usd")]


@pytest.fixture(scope="module", params=[1, 2, 3], ids=["base", "upside", "downside"])
def built(request, tmp_path_factory):
    d = tmp_path_factory.mktemp(f"l{request.param}")
    path, layout = build_03(request.param, out=d / "03.xlsx")
    return path, layout, recalc(path, d / "rc"), run(build_lbo_inputs(request.param))


def _check(v, cell, ref):
    bad = []
    for sheet, key, rkey, kind in SERIES:
        for t, (a, b) in enumerate(zip(v.fcst(sheet, key), ref[rkey])):
            if not close(a, b, kind):
                bad.append(f"{sheet}.{key}[{t}] {a} vs {b}")
    for sheet, key, rkey, kind in CONSTS:
        if not close(v.const(sheet, key), ref[rkey], kind):
            bad.append(f"{sheet}.{key} {v.const(sheet, key)} vs {ref[rkey]}")
    if abs(v.const("Returns", "irr") - ref["irr"]) > 1e-6:
        bad.append(f"irr {v.const('Returns', 'irr')} vs {ref['irr']}")
    for i, row in enumerate(ref["grid_price_mult"]):
        for j, x in enumerate(row):
            if abs(cell("Sensitivity", f"{'CDEFG'[j]}{6 + i}") - x) > 1e-9:
                bad.append(f"price grid {i},{j}")
    for i, row in enumerate(ref["grid_year_mult"]):
        for j, x in enumerate(row):
            if abs(cell("Sensitivity", f"{'CDEFG'[j]}{16 + i}") - x) > 1e-9:
                bad.append(f"year grid {i},{j}")
    return bad


def test_libreoffice_matches_reference(built):
    path, layout, rc, ref = built
    v = Values(rc, layout)
    assert not v.errors() and v.const("Checks", "master") == 0
    bad = _check(v, lambda s, a: v.wb[s][a].value, ref)
    assert not bad, bad[:20]


def test_formulas_engine_matches_reference(built):
    path, layout, _, ref = built
    v = FormulasValues(path, layout)
    bad = _check(v, v._get, ref)
    assert not bad, bad[:20]


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report


def test_sources_and_uses_tie_to_information_statement():
    """Sources excluding balance-sheet cash = DEFM14C Note 3(i) proceeds + rollover (Note 2(a))."""
    ref = run(build_lbo_inputs(1))
    assert abs(ref["sources_ex_cash"] - (3026.375 + 1170.028 + 2200.0 + 3507.898 + 741.965)) < 1e-9
    assert abs(ref["uses"] - (10372.387 - 0.0 + 202.425 + 31.8 + 71.5)) < 1e-6  # Note 2(a) consideration + fees + costs
