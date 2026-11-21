"""M10: workbook 08 (dashboard) shows the delivered workbooks' numbers, which equal the Python references.

Verify: pytest -q tests/test_dashboard.py
"""
import json

import pytest

from ledgerline.audit.audit import audit
from ledgerline.build.recalc import Values, recalc
from ledgerline.build.workbooks import OUT, build_08


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("dash")
    path, layout = build_08(out=d / "08.xlsx")
    return path, layout, recalc(path, d / "rc")


@pytest.fixture(scope="module")
def refs():
    from ledgerline.data.fpa import load as fpa_load
    from ledgerline.data.group import load as group_load
    from ledgerline.models.assumptions import build_inputs
    from ledgerline.models.mna_inputs import build_mna_inputs
    from ledgerline.models.valuation_inputs import build_val_inputs
    from ledgerline.ref import credit, dcf, fpa, group, lab, mna
    inp = build_inputs("COST")
    v = build_val_inputs(inp)
    d, mn, g, f = dcf.run(inp, v), mna.run(build_mna_inputs(1, 3)), group.run(group_load()), fpa.run(fpa_load())
    lb = lab.run(inp, v)
    cr = credit.run()["results"]
    return {
        "DCF price, perpetuity growth ($)": d["price_gordon"], "DCF price, exit multiple ($)": d["price_exit"],
        "Perpetual growth implied by the market price": d["implied_growth_market"],
        "Adjusted EPS accretion, FY2025": mn["acc_adj"][0], "Adjusted EPS accretion, FY2026": mn["acc_adj"][1],
        "Net income attributable to the parent ($m)": g["st"]["ni_parent"], "Total assets ($m)": g["st"]["total_assets"],
        "FY2026 EBITDA: outlook ($m)": f["fy"]["ebitda_actual"], "June forecast MAPE": f["mape"],
        "Monte Carlo median price, perpetuity growth ($)": lb["mc"]["gordon"]["p"][0.5],
        "Costco scorecard rating": cr[0]["rating"],
        "Borrowers breaching covenants under stress (of 11)": sum(x["s_breach"] for x in cr),
    }


def test_dashboard_values_equal_references(built, refs):
    _, layout, _ = built
    got = {lab: v for _, lab, v, _, _ in layout["values"]}
    for k, x in refs.items():
        assert (got[k] == x) if isinstance(x, str) else abs(got[k] - x) <= 1e-9 * max(1, abs(x)), (k, got[k], x)


def test_every_workbook_passes_and_dashboard_master_is_green(built):
    path, layout, rc = built
    from openpyxl import load_workbook
    wb = load_workbook(rc, data_only=True)
    assert wb["Checks"]["B6"].value == 0 and wb["Checks"]["B4"].value == 0


def test_audit_clean(built):
    path, layout, rc = built
    findings, _, report = audit(path, rc, layout)
    assert not [f for f in findings if f.severity in ("high", "medium")], report
