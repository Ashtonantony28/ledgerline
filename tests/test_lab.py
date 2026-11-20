"""M8: workbook 07 (scenario lab). The live model under every stress case and a manual shift equals a full
re-run of the Python references with the same shifts, on LibreOffice and `formulas`; Monte Carlo is reproducible.

Verify: pytest -q tests/test_lab.py
"""
import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_07
from ledgerline.models.assumptions import build_inputs
from ledgerline.models.valuation_inputs import build_val_inputs
from ledgerline.ref import lab as ref_lab
from ledgerline.verify import close

TRIALS = 300  # the delivered workbook uses the spec's 10,000; tests only need the plumbing
MANUAL = {"gross_margin": 0.003, "wacc": -0.004, "store_openings": 5.0}
CASES = [(0, None), (1, None), (2, None), (3, None), (4, None), (0, MANUAL), (4, MANUAL)]


@pytest.fixture(scope="module")
def base_inputs():
    inp = build_inputs("COST")
    return inp, build_val_inputs(inp)


def expected(base_inputs, stress, manual):
    inp, v = base_inputs
    sp = ref_lab.spec()
    shifts = dict(sp["stress"][stress - 1]["shifts"]) if stress else {}
    for k, x in (manual or {}).items():
        shifts[k] = shifts.get(k, 0.0) + x
    return ref_lab.price(inp, v, shifts)


@pytest.fixture(scope="module", params=CASES, ids=["base", "s1", "s2", "s3", "s4", "manual", "s4+manual"])
def built(request, tmp_path_factory, base_inputs):
    stress, manual = request.param
    d = tmp_path_factory.mktemp("lab")
    path, layout = build_07(stress, manual, trials=TRIALS, out=d / "07.xlsx")
    return path, layout, recalc(path, d / "rc"), expected(base_inputs, stress, manual)


def test_libreoffice_live_price_matches_reference(built):
    path, layout, rc, (pg, px) = built
    v = Values(rc, layout)
    assert not v.errors() and v.const("Checks", "master") == 0
    assert close(v.const("Lab", "live_price_g"), pg, "ratio") and close(v.const("Lab", "live_price_x"), px, "ratio"), \
        (v.const("Lab", "live_price_g"), pg, v.const("Lab", "live_price_x"), px)


def test_formulas_engine_live_price_matches_reference(built):
    path, layout, _, (pg, px) = built
    v = FormulasValues(path, layout)
    assert close(v.const("Lab", "live_price_g"), pg, "ratio") and close(v.const("Lab", "live_price_x"), px, "ratio")


def test_audit_clean(built):
    path, layout, rc, _ = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report


def test_tornado_and_stress_tables_are_reference_reruns(base_inputs):
    inp, v = base_inputs
    r = ref_lab.run(inp, v, trials=50)
    for t in r["tornado"]:
        assert t["low"] == ref_lab.price(inp, v, {t["key"]: -t["step"]})
    swings = [t["swing"] for t in r["tornado"]]
    assert swings == sorted(swings, reverse=True)
    assert r["spider"]["wacc"][2] == r["base"]


def test_monte_carlo_is_seeded_and_reproducible(base_inputs):
    inp, v = base_inputs
    a, b = ref_lab.run(inp, v, trials=500), ref_lab.run(inp, v, trials=500)
    assert a["mc"] == b["mc"] and sum(a["mc"]["gordon"]["counts"]) == 500
    p = a["mc"]["gordon"]["p"]
    assert p[0.05] < p[0.50] < p[0.95]
