"""M3: workbook 02 (DCF + comps) matches the reference on LibreOffice and `formulas`.

Verify: pytest -q tests/test_valuation.py
"""
import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_02
from ledgerline.models.assumptions import build_inputs
from ledgerline.models.valuation_inputs import build_val_inputs
from ledgerline.ref.dcf import run
from ledgerline.verify import close

CONSTS = [("WACC", "beta_adj", "beta_adj", "ratio"), ("WACC", "ke", "ke", "ratio"), ("WACC", "wacc", "wacc", "ratio"),
          ("DCF", "sum_pv", "sum_pv", "usd"), ("DCF", "net_debt", "net_debt", "usd"), ("DCF", "ev_g", "ev_gordon", "usd"),
          ("DCF", "price_g", "price_gordon", "ratio"), ("DCF", "tv_share_g", "tv_share_gordon", "ratio"),
          ("DCF", "exit_mult", "exit_multiple", "ratio"), ("DCF", "ev_x", "ev_exit", "usd"), ("DCF", "price_x", "price_exit", "ratio"),
          ("DCF", "implied_mult", "implied_exit_multiple", "ratio"), ("DCF", "implied_g", "implied_growth_from_exit", "ratio"),
          ("DCF", "implied_g_mkt", "implied_growth_market", "ratio"), ("DCF", "upside_g", "upside_gordon", "ratio")]
COLS = "CDEFG"


@pytest.fixture(scope="module", params=[1, 3], ids=["base", "downside"])
def built(request, tmp_path_factory):
    d = tmp_path_factory.mktemp(f"v{request.param}")
    path, layout = build_02("COST", scenario=request.param, out=d / "02.xlsx")
    inp = build_inputs("COST", request.param, 0)
    return path, layout, recalc(path, d / "rc"), run(inp, build_val_inputs(inp))


def _check(v, cell, ref):
    bad = []
    for sheet, key, rkey, kind in CONSTS:
        if not close(v.const(sheet, key), ref[rkey], kind):
            bad.append(f"{sheet}.{key}: {v.const(sheet, key)} vs {ref[rkey]}")
    for i, row in enumerate(ref["grid_gordon"]):
        for j, x in enumerate(row):
            if not close(cell("Sensitivity", f"{COLS[j]}{7 + i}"), x, "ratio"):
                bad.append(f"gordon grid {i},{j}")
    for i, row in enumerate(ref["grid_exit"]):
        for j, x in enumerate(row):
            if not close(cell("Sensitivity", f"{COLS[j]}{17 + i}"), x, "ratio"):
                bad.append(f"exit grid {i},{j}")
    for k, (lo, hi) in enumerate(ref["football"].values()):
        if not (close(cell("Football", f"B{5 + k}"), lo, "ratio") and close(cell("Football", f"C{5 + k}"), hi, "ratio")):
            bad.append(f"football row {k}")
    for k, row in enumerate(ref["comps"]["rows"]):
        for col, key in (("K", "ev"), ("Q", "ev_ebitda"), ("R", "pe")):
            if not close(cell("Comps", f"{col}{6 + k}"), row[key], "ratio"):
                bad.append(f"comps {row['ticker']} {key}")
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


def test_ufcf_matches(built):
    path, layout, rc, ref = built
    v = Values(rc, layout)
    assert all(close(a, b, "usd") for a, b in zip(v.fcst("DCF", "ufcf"), ref["ufcf"]))


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report
