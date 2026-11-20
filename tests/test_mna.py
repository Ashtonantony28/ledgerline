"""M5: workbook 04 (DICK'S / Foot Locker) matches the reference on LibreOffice and `formulas`.

Verify: pytest -q tests/test_mna.py
"""
import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import FormulasValues, Values, recalc
from ledgerline.build.workbooks import build_04
from ledgerline.models.mna_inputs import build_mna_inputs
from ledgerline.ref.mna import run, transaction
from ledgerline.verify import MNA_OUTPUTS, close

SERIES = MNA_OUTPUTS
CONSTS = [("Transaction", k, k, "usd") for k in ("consideration", "stock_value", "stake_fv", "stake_gain", "cash_uses", "new_debt",
                                                 "issuance_cost", "cash_used", "cash_close", "dtl", "net_assets", "goodwill",
                                                 "bargain_gain", "offer_ev", "pf_debt", "pf_net_debt")] + \
         [("Transaction", "new_shares", "new_shares", "ratio"), ("Transaction", "ev_ebitda_ltm", "ev_ebitda_ltm", "ratio"),
          ("Transaction", "ev_ebitda_fwd", "ev_ebitda_fwd", "ratio")] + \
         [("ProForma", k, k, "ratio") for k in ("contrib_rev", "contrib_ebitda", "contrib_ni", "own_dks", "own_fl", "sa_leverage")]
CASES = [(1, 3), (2, 3), (3, 3), (1, 1), (1, 2)]


@pytest.fixture(scope="module", params=CASES, ids=["base-actual", "upside-actual", "downside-actual", "base-cash", "base-stock"])
def built(request, tmp_path_factory):
    sc, st = request.param
    d = tmp_path_factory.mktemp(f"m{sc}{st}")
    path, layout = build_04(sc, st, out=d / "04.xlsx")
    return path, layout, recalc(path, d / "rc"), run(build_mna_inputs(sc, st))


def _check(v, cell, ref):
    bad = []
    for sheet, key, rkey, kind in SERIES:
        for t, (a, b) in enumerate(zip(v.fcst(sheet, key), ref[rkey])):
            if not close(a, b, kind):
                bad.append(f"{sheet}.{key}[{t}] {a} vs {b}")
    for sheet, key, rkey, kind in CONSTS:
        if not close(v.const(sheet, key), ref[rkey], kind):
            bad.append(f"{sheet}.{key} {v.const(sheet, key)} vs {ref[rkey]}")
    for i, row in enumerate(ref["grid_price_pct"]):
        for j, x in enumerate(row):
            if abs(cell("Sensitivity", f"{'CDEFG'[j]}{6 + i}") - x) > 1e-9:
                bad.append(f"price grid {i},{j}: {cell('Sensitivity', f'{chr(67 + j)}{6 + i}')} vs {x}")
    for i, row in enumerate(ref["grid_year_syn"]):
        for j, x in enumerate(row):
            if abs(cell("Sensitivity", f"{'CDEF'[j]}{16 + i}") - x) > 1e-9:
                bad.append(f"synergy grid {i},{j}")
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


@pytest.mark.parametrize("structure,expected", [(1, 2_318.102), (2, 1_998.277)])
def test_consideration_ties_to_prospectus(structure, expected):
    """Consideration transferred = 424B3 note 3A1 (all cash) and 3A3 (all stock), to rounding of share counts."""
    tr = transaction(build_mna_inputs(1, structure))
    assert abs(tr["consideration"] - expected) < 0.05


def test_actual_election_ties_to_10k():
    """Actual mix: consideration within 0.2% of the $2,512.7m in DICK'S FY2025 10-K Note 2; ~9.5m shares issued."""
    tr = transaction(build_mna_inputs(1, 3))
    assert abs(tr["consideration"] / 2_512.662 - 1) < 0.002
    assert abs(tr["new_shares"] - 9.545) < 0.01
