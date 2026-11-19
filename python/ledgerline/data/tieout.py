"""Tie-out checks: the normalised history must agree with the as-filed statements.

Hard checks fail the build (accounting identities that hold in every 10-K). Soft checks are
reported as warnings (large plugs, EPS rounding) for a human to review and, if needed, to
resolve with a cited override.
"""
from __future__ import annotations

from dataclasses import dataclass

from .normalise import History

TOL_USD = 0.5e6          # filings are in millions; half a million covers rounding
TOL_EPS = 0.02           # EPS is rounded to cents and uses weighted shares
PLUG_WARN_SHARE = 0.10   # warn when a plug exceeds 10% of its statement scale


@dataclass
class Check:
    name: str
    period: str
    expected: float
    actual: float
    tol: float
    hard: bool = True

    @property
    def ok(self) -> bool:
        return abs(self.expected - self.actual) <= self.tol


def tieout(h: History) -> list[Check]:
    v = h.values
    out: list[Check] = []
    labels = h.fy_labels()
    for i, fy in enumerate(labels):
        out.append(Check("assets = liabilities + equity (reported L&E)", fy, v["total_assets"][i], v["total_le"][i], TOL_USD))
        out.append(Check("L&E = total liabilities + temporary equity + total equity", fy, v["total_le"][i],
                         v["total_liabilities"][i] + v["temp_equity"][i] + v["total_equity"][i], TOL_USD))
        out.append(Check("total equity = parent + NCI", fy, v["total_equity"][i],
                         v["parent_equity"][i] + v["nci_equity"][i], TOL_USD))
        out.append(Check("net income = total - NCI share", fy, v["net_income"][i],
                         v["net_income_total"][i] - v["nci_income"][i], TOL_USD))
        out.append(Check("CFO + CFI + CFF + FX = change in cash", fy, v["net_change_cash"][i],
                         v["cfo"][i] + v["cfi"][i] + v["cff"][i] + v["fx_effect"][i], TOL_USD))
        if i > 0:
            out.append(Check("cash roll-forward (CF basis)", fy, v["cash_cf_basis"][i],
                             v["cash_cf_basis"][i - 1] + v["net_change_cash"][i], TOL_USD))
        if v["shares_diluted"][i]:
            out.append(Check("diluted EPS ~ NI / diluted shares", fy, v["eps_diluted"][i],
                             v["net_income"][i] / v["shares_diluted"][i], TOL_EPS, hard=False))
        scales = {"other_opex": v["revenue"][i], "other_nonop_income": v["revenue"][i],
                  "other_below_tax": v["revenue"][i], "other_current_assets": v["total_assets"][i],
                  "other_nc_assets": v["total_assets"][i], "other_current_liabilities": v["total_assets"][i],
                  "other_nc_liabilities": v["total_assets"][i]}
        for key, scale in scales.items():
            out.append(Check(f"plug {key} small vs scale", fy, 0.0, v[key][i], PLUG_WARN_SHARE * abs(scale), hard=False))
    return out


def report(h: History, checks: list[Check]) -> str:
    hard_fail = [c for c in checks if c.hard and not c.ok]
    soft_fail = [c for c in checks if not c.hard and not c.ok]
    lines = [f"# Tie-out: {h.ticker} ({h.entity})", "",
             f"Periods: {', '.join(f'{l} (ends {d})' for l, d in zip(h.fy_labels(), h.period_ends))}", "",
             f"Hard checks: {sum(c.ok for c in checks if c.hard)}/{sum(c.hard for c in checks)} pass",
             f"Soft checks: {sum(c.ok for c in checks if not c.hard)}/{sum(not c.hard for c in checks)} pass", ""]
    for title, group in (("Hard failures", hard_fail), ("Warnings", soft_fail)):
        if group:
            lines += [f"## {title}", "", "| check | period | expected | actual | diff |", "|---|---|---|---|---|"]
            lines += [f"| {c.name} | {c.period} | {c.expected:,.0f} | {c.actual:,.0f} | {c.actual - c.expected:,.0f} |" for c in group]
            lines.append("")
    return "\n".join(lines)
