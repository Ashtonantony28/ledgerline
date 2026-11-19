"""M1: the committed history snapshots tie out to the as-filed statements."""
import pytest

from ledgerline.data.history import load, load_maturities
from ledgerline.data.normalise import eval_linear
from ledgerline.data.tieout import tieout

TICKERS = ["COST", "WMT", "TGT", "BJ", "DG", "KR", "HD", "LOW", "SKX"]


@pytest.mark.parametrize("ticker", TICKERS)
def test_hard_tieouts_pass(ticker):
    h = load(ticker)
    failures = [c for c in tieout(h) if c.hard and not c.ok]
    assert not failures, "\n".join(f"{c.name} {c.period}: {c.actual - c.expected:,.0f}" for c in failures)


def test_costco_known_values():
    """Spot values read from Costco's FY2026 10-K (accession 0000909832-26-000093)."""
    h = load("COST")
    i = h.fy_labels().index("FY2026")
    assert h.values["revenue"][i] == 303_154e6
    assert h.values["net_income"][i] == 9_226e6
    assert h.values["total_assets"][i] == 89_045e6
    assert h.values["stores"][i] == 939


def test_every_cell_has_provenance():
    h = load("COST")
    for key, srcs in h.source.items():
        assert all(srcs), f"{key} has a cell without a source"


def test_maturities_sum_to_principal():
    m = load_maturities("COST")
    assert sum(x["value"] for x in m["maturities"]) == 6_175e6  # DebtInstrumentCarryingAmount, FY2026 10-K


def test_eval_linear():
    assert eval_linear("a - b + c", {"a": 5, "b": 3, "c": 1}) == 3
    with pytest.raises(ValueError):
        eval_linear("a b", {"a": 1, "b": 2})
