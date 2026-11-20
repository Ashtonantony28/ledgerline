"""M6: workbook 05 (group close and consolidation) matches ref/group.py on LibreOffice and `formulas`.

Verify: pytest -q tests/test_group.py
"""
import filecmp

import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, recalc
from ledgerline.build.workbooks import build_05
from ledgerline.data import group as gen
from ledgerline.ref.group import run
from ledgerline.verify import group_compare as compare, group_expected as expected

from openpyxl import load_workbook


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("g")
    path, layout = build_05(out=d / "05.xlsx")
    return path, layout, recalc(path, d / "rc"), expected(run(gen.load()))


def test_libreoffice_matches_reference(built):
    path, layout, rc, exp = built
    wb = load_workbook(rc, data_only=True)
    get = lambda s, c: wb[s][c].value
    assert get(*layout["addr"]["master"]) == 0
    bad = compare(get, layout["addr"], exp)
    assert not bad, bad[:20]


def test_formulas_engine_matches_reference(built):
    path, layout, _, exp = built
    v = FormulasValues(path, layout)
    bad = compare(v._get, layout["addr"], exp)
    assert not bad, bad[:20]


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report


def test_reference_identities():
    r = run(gen.load())
    st = r["st"]
    assert abs(st["total_assets"] - st["total_liabilities"] - st["total_equity"]) < 1e-9
    assert abs(r["cta_plug"] - r["cta_analytic"]) < 1e-9
    assert all(abs(v) < 1e-9 for v in r["elim_sums"].values())
    assert abs(r["cons_cf"]["cash_open"] + r["cons_cf"]["net"] - r["cons_cf"]["cash_close"]) < 1e-9


def test_generator_is_deterministic(tmp_path):
    gen.write(gen.generate(), tmp_path)
    for f in ("accounts.csv", "opening.csv", "tb_unadjusted.csv", "close.yaml"):
        assert filecmp.cmp(tmp_path / f, gen.OUT / f, shallow=False), f
