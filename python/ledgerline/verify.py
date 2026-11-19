"""Compare a recalculated workbook against its Python reference (tolerances: ADR 0005).

Currency lines: |workbook - reference| <= $0.01 (model units are $m, so 1e-8).
Per-share and ratio lines: relative error <= 1e-9 (absolute 1e-9 near zero).
"""
from __future__ import annotations

from dataclasses import dataclass

TOL_USD_M = 0.01 / 1e6
TOL_REL = 1e-9

THREE_STATEMENT_OUTPUTS = [  # (sheet, row key, reference key, kind)
    ("IS", "revenue", "revenue", "usd"), ("IS", "cogs", "cogs", "usd"), ("IS", "sga", "sga", "usd"),
    ("IS", "operating_income", "operating_income", "usd"), ("IS", "interest_expense", "interest_expense", "usd"),
    ("IS", "other_nonop_income", "interest_income", "usd"), ("IS", "pretax_income", "pretax_income", "usd"),
    ("IS", "income_tax", "income_tax", "usd"), ("IS", "net_income", "net_income", "usd"),
    ("IS", "shares_diluted", "shares_diluted", "ratio"), ("IS", "eps_diluted", "eps_diluted", "ratio"),
    ("IS", "ebitda", "ebitda", "usd"),
    ("BS", "cash", "cash", "usd"), ("BS", "receivables", "receivables", "usd"), ("BS", "inventory", "inventory", "usd"),
    ("BS", "ppe_net", "ppe_net", "usd"), ("BS", "total_assets", "total_assets", "usd"),
    ("BS", "accounts_payable", "accounts_payable", "usd"), ("BS", "ocl", "ocl", "usd"), ("BS", "debt", "debt", "usd"),
    ("BS", "revolver", "revolver", "usd"), ("BS", "total_liabilities", "total_liabilities", "usd"),
    ("BS", "parent_equity", "parent_equity", "usd"),
    ("CF", "cfo", "cfo", "usd"), ("CF", "cfi", "cfi", "usd"), ("CF", "cff", "cff", "usd"),
    ("CF", "dividends", "dividends", "usd"), ("CF", "special_dividends", "special_dividends", "usd"),
    ("CF", "buybacks", "buybacks", "usd"), ("CF", "net_change_cash", "net_change_cash", "usd"),
]


@dataclass
class Mismatch:
    sheet: str
    key: str
    period: int
    workbook: object
    reference: float

    def __str__(self) -> str:
        return f"{self.sheet}.{self.key}[{self.period}]: workbook={self.workbook!r} reference={self.reference!r}"


def close(a, b: float, kind: str) -> bool:
    if not isinstance(a, (int, float)):
        return False
    if kind == "usd":
        return abs(a - b) <= TOL_USD_M
    return abs(a - b) <= max(TOL_REL * abs(b), TOL_REL)


def compare(values, ref: dict[str, list[float]], outputs) -> list[Mismatch]:
    bad = []
    for sheet, key, rkey, kind in outputs:
        got = values.fcst(sheet, key)
        for t, (a, b) in enumerate(zip(got, ref[rkey])):
            if not close(a, b, kind):
                bad.append(Mismatch(sheet, key, t, a, b))
    return bad
