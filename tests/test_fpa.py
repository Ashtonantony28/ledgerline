"""M7: workbook 06 (FP&A budget, rolling forecast, variance) matches ref/fpa.py on LibreOffice and `formulas`.

Verify: pytest -q tests/test_fpa.py
"""
import filecmp

import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_06
from ledgerline.data import fpa as gen
from ledgerline.ref.fpa import run
from ledgerline.verify import fpa_compare


@pytest.fixture(scope="module", params=[1, 2, 3], ids=["base", "upside", "downside"])
def built(request, tmp_path_factory):
    d = tmp_path_factory.mktemp(f"f{request.param}")
    path, layout = build_06(request.param, out=d / "06.xlsx")
    return path, layout, recalc(path, d / "rc"), run(gen.load(), request.param)


def test_libreoffice_matches_reference(built):
    path, layout, rc, ref = built
    v = Values(rc, layout)
    assert not v.errors() and v.const("Checks", "master") == 0
    assert v.const("PnL", "min_cash_month") == layout["timeline"]["labels"][ref["min_cash_month"]]
    bad = fpa_compare(v, ref)
    assert not bad, bad[:20]


def test_formulas_engine_matches_reference(built):
    path, layout, _, ref = built
    bad = fpa_compare(FormulasValues(path, layout), ref)
    assert not bad, bad[:20]


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report


def test_bridges_sum_in_reference():
    r = run(gen.load())
    for s in ("ytd", "fy"):
        x = r[s]
        assert abs(x["rev_budget"] + x["price"] + x["rev_volume"] + x["rev_mix"] - x["rev_actual"]) < 1e-9
        assert abs(x["ebitda_bridge"] - x["ebitda_actual"]) < 1e-9
        assert abs(x["heads"] + x["rate"] + x["np"] - x["opex_var"]) < 1e-9


def test_generator_is_deterministic(tmp_path):
    gen.write(gen.generate(), tmp_path)
    for f in ("actuals.csv", "prior_forecast.csv"):
        assert filecmp.cmp(tmp_path / f, gen.OUT / f, shallow=False), f
