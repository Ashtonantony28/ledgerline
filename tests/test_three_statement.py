"""M2: workbook 01 recalculated by LibreOffice and by `formulas` matches the Python reference.

Verify: pytest -q tests/test_three_statement.py
"""
import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_01
from ledgerline.models.assumptions import build_inputs
from ledgerline.ref.three_statement import run
from ledgerline.verify import THREE_STATEMENT_OUTPUTS, compare


@pytest.fixture(scope="module", params=[1, 2, 3], ids=["base", "upside", "downside"])
def built(request, tmp_path_factory):
    d = tmp_path_factory.mktemp(f"wb{request.param}")
    path, layout = build_01("COST", scenario=request.param, circ=0, out=d / "01.xlsx")
    rc = recalc(path, d / "rc")
    return request.param, path, layout, rc


def test_libreoffice_matches_reference(built):
    scenario, _, layout, rc = built
    v = Values(rc, layout)
    assert not v.errors()
    bad = compare(v, run(build_inputs("COST", scenario, 0)), THREE_STATEMENT_OUTPUTS)
    assert not bad, "\n".join(map(str, bad[:20]))


def test_master_check_passes(built):
    _, _, layout, rc = built
    assert Values(rc, layout).const("Checks", "master") == 0


def test_formulas_engine_matches_reference(built):
    scenario, path, layout, _ = built
    v = FormulasValues(path, layout)
    bad = compare(v, run(build_inputs("COST", scenario, 0)), THREE_STATEMENT_OUTPUTS)
    assert not bad, "\n".join(map(str, bad[:20]))


def test_audit_clean(built):
    _, path, layout, rc = built
    findings, _, report = audit(path, rc, layout)
    high = [f for f in findings if f.severity in ("high", "medium")]
    assert not high, report


@pytest.mark.parametrize("scenario", [1, 2, 3])
def test_reference_circular_mode_balances_and_converges(scenario):
    """Average-balance interest (circ=1) is checked against the reference's fixed point.

    LibreOffice headless does not iterate this model to convergence, and `formulas` breaks
    cycles instead of iterating (docs/known-differences.md), so the workbook's circ=1 mode is
    verified in Excel before release (tools/excel_check.py); here we prove the reference solves it.
    """
    r = run(build_inputs("COST", scenario, 1))
    assert max(abs(x) for x in r["balance_check"]) < 1e-6
    r0 = run(build_inputs("COST", scenario, 0))
    # Average-balance interest differs from opening-balance interest but only modestly.
    assert all(abs(a - b) / abs(b) < 0.05 for a, b in zip(r["net_income"], r0["net_income"]))
