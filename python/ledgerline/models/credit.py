"""Workbook 09: credit analysis of the covered retailers (docs/models/credit.md).

Columns are borrowers, not periods: each column is one company's latest 10-K, so every row keeps one formula
across the borrowers and the audit's consistency rule still applies.
"""
from __future__ import annotations

from datetime import date

from ..build.grid import Model, Timeline
from ..ref.credit import ITEMS, Borrower

LABEL = {
    "revenue": "Revenue", "operating_income": "Operating income (EBIT)", "da": "Depreciation and amortisation",
    "interest_expense": "Interest expense (gross, as tagged)", "interest_nonop_net": "Net non-operating interest (memo)",
    "debt": "Debt (current + long-term + short-term borrowings)", "leases": "Operating lease liabilities",
    "cash": "Cash", "st_investments": "Short-term investments", "total_assets": "Total assets",
    "total_liabilities": "Total liabilities", "current_assets": "Current assets", "current_liabilities": "Current liabilities",
    "retained_earnings": "Retained earnings", "total_equity": "Total equity", "temp_equity": "Temporary equity",
    "cfo": "Cash from operations", "capex": "Capital expenditure (cash sign)", "net_income": "Net income",
}
J = "Judgement: spec/CREDIT.yaml."


def timeline(bs: list[Borrower]) -> Timeline:
    return Timeline([b.fy_end.isoformat() for b in bs], [b.ticker for b in bs], len(bs))


def add_credit(m: Model, bs: list[Borrower], sp: dict) -> None:
    sc, al, cv, cap, st = sp["scorecard"], sp["altman"], sp["covenants"], sp["capacity"], sp["stress"]
    I = lambda k: "{Inputs.$%s}" % k
    nR = len(sc["ratings"])

    # ---------------------------------------------------------------- Inputs
    s = m.sheet("Inputs", "Inputs: Altman Z' coefficients, scorecard grid, covenants, capacity and stress assumptions")
    s.section("Altman Z' (book-equity form)")
    for k, lab in (("wc_ta", "Working capital / total assets"), ("re_ta", "Retained earnings / total assets"),
                   ("ebit_ta", "EBIT / total assets"), ("eq_tl", "Book equity / total liabilities"), ("sales_ta", "Sales / total assets")):
        s.add(f"z_{k}", f"  Coefficient: {lab}", "x", const=al["coef"][k], fmt="0.000", const_note=al["source"])
    s.add("z_distress", "  Distress zone below", "x", const=al["distress"], fmt="0.00", const_note=al["source"])
    s.add("z_safe", "  Safe zone above", "x", const=al["safe"], fmt="0.00", const_note=al["source"])
    s.blank()
    s.section("Scorecard grid (simplified, judgement)")
    for k, lab in enumerate(sc["ratings"], 1):
        s.add(f"rating_{k}", f"  Band {k}: rating", "", const=lab, fmt="text", const_note=J)
    for k, b in enumerate(sc["leverage_bounds"], 1):
        s.add(f"levb_{k}", f"  Leverage: upper bound of band {k}", "x", const=b, fmt="x", const_note=J)
    for k, b in enumerate(sc["coverage_bounds"], 1):
        s.add(f"covb_{k}", f"  Coverage: lower bound of band {k}", "x", const=b, fmt="x", const_note=J)
    for k, p in enumerate(sc["pd_1y"], 1):
        s.add(f"pd_{k}", f"  Band {k}: one-year PD (illustrative)", "%", const=p, fmt="0.00%", const_note=J)
    s.add("lev_w", "  Weight on the leverage band", "%", const=sc["leverage_weight"], fmt="pct", const_note=J)
    s.add("notches", "  Notches down in the Altman distress zone", "count", const=sc["distress_notches"], fmt="n", const_note=J)
    s.add("n_bands", "  Number of bands", "count", const=nR, fmt="n", const_note="Length of the grid above.")
    s.blank()
    s.section("Covenants, capacity, stress (judgement)")
    s.add("max_lev", "Covenant: maximum lease-adjusted leverage", "x", const=cv["max_leverage"], fmt="x", const_note=J)
    s.add("min_cov", "Covenant: minimum EBITDA / interest", "x", const=cv["min_coverage"], fmt="x", const_note=J)
    s.add("cap_lev", "Capacity: target leverage", "x", const=cap["target_leverage"], fmt="x", const_note=J)
    s.add("cap_cov", "Capacity: minimum coverage", "x", const=cap["min_coverage"], fmt="x", const_note=J)
    s.add("cap_rate", "Capacity: cost of incremental debt", "%", const=cap["marginal_rate"], fmt="pct", const_note=J)
    s.add("shock", "Stress: EBITDA decline", "%", const=st["ebitda_shock"], fmt="pct", const_note=J)
    s.add("rate_shock", "Stress: rate rise on floating debt", "%", const=st["rate_shock"], fmt="pct", const_note=J)
    s.add("floating", "Stress: floating share of debt", "%", const=st["floating_share"], fmt="pct", const_note=J)
    rng = lambda pre: "%s:%s" % (I(f"{pre}_1"), I(f"{pre}_{nR if pre in ('rating', 'pd') else nR - 1}"))

    # ---------------------------------------------------------------- Spreads (inputs)
    sp_ = m.sheet("Spreads", "Borrower spreads: latest 10-K per company, $m (XBRL, per-cell sources in the notes)")
    for k in ITEMS:
        r = sp_.add(k, LABEL[k], "$m", hist=[b.v[k] for b in bs], style="input", fmt="m")
        r.note = "Latest fiscal year per borrower. " + " | ".join(f"{b.ticker} ({b.fy_end}): {b.src[k]}" for b in bs)
    sp_.add("bs_tie", "Assets - liabilities - equity - temporary equity", "$m",
            hist="={total_assets}-{total_liabilities}-{total_equity}-{temp_equity}", fmt="m1")
    sp_.cell("A5", "Borrower")

    # ---------------------------------------------------------------- Credit
    c = m.sheet("Credit", "Credit metrics, Altman Z', scorecard rating, covenant headroom and debt capacity")
    c.cell("A5", "Borrower")
    S = lambda k: "{Spreads.%s}" % k

    def scorecard(prefix: str, lev: str, cov: str, z: str):
        c.add(f"{prefix}lev_band", "  Leverage band", "band", all="=1+SUMPRODUCT((%s<{%s})*1)" % (rng("levb"), lev), fmt="n")
        c.add(f"{prefix}cov_band", "  Coverage band", "band", all="=1+SUMPRODUCT((%s>{%s})*1)" % (rng("covb"), cov), fmt="n")
        c.add(f"{prefix}idx", "  Rating band (weighted, rounded, distress notch)", "band",
              all="=MIN(%s,ROUND(%s*{%slev_band}+(1-%s)*{%scov_band},0)+IF({%s}<%s,%s,0))" % (
                  I("n_bands"), I("lev_w"), prefix, I("lev_w"), prefix, z, I("z_distress"), I("notches")), fmt="n")
        c.add(f"{prefix}rating", "  Rating", "", all="=INDEX(%s,{%sidx})" % (rng("rating"), prefix), fmt="text")
        c.add(f"{prefix}pd", "  One-year PD", "%", all="=INDEX(%s,{%sidx})" % (rng("pd"), prefix), fmt="0.00%")

    def z_formula(ebit: str) -> str:
        return ("=%s*(%s-%s)/%s+%s*%s/%s+%s*%s/%s+%s*%s/%s+%s*%s/%s" % (
            I("z_wc_ta"), S("current_assets"), S("current_liabilities"), S("total_assets"),
            I("z_re_ta"), S("retained_earnings"), S("total_assets"), I("z_ebit_ta"), ebit, S("total_assets"),
            I("z_eq_tl"), S("total_equity"), S("total_liabilities"), I("z_sales_ta"), S("revenue"), S("total_assets")))

    c.section("Earnings and debt")
    c.add("ebitda", "EBITDA", "$m", all="=%s+%s" % (S("operating_income"), S("da")), fmt="m")
    c.add("interest", "Interest for coverage (gross; net non-operating where gross is not tagged)", "$m",
          all="=IF(%s>0,%s,%s)" % (S("interest_expense"), S("interest_expense"), S("interest_nonop_net")), fmt="m")
    c.add("adj_debt", "Lease-adjusted debt", "$m", all="=%s+%s" % (S("debt"), S("leases")), fmt="m")
    c.add("net_debt", "Lease-adjusted net debt", "$m", all="={adj_debt}-%s-%s" % (S("cash"), S("st_investments")), fmt="m")
    c.add("fcf", "Free cash flow", "$m", all="=%s+%s" % (S("cfo"), S("capex")), fmt="m")
    c.section("Ratios")
    c.add("leverage", "Lease-adjusted debt / EBITDA", "x", all="={adj_debt}/{ebitda}", fmt="x")
    c.add("net_leverage", "Lease-adjusted net debt / EBITDA", "x", all="={net_debt}/{ebitda}", fmt="x")
    c.add("coverage", "EBITDA / interest", "x", all="={ebitda}/{interest}", fmt="x")
    c.add("ebit_coverage", "EBIT / interest", "x", all="=%s/{interest}" % S("operating_income"), fmt="x")
    c.add("fcf_debt", "Free cash flow / lease-adjusted debt", "%", all="={fcf}/{adj_debt}", fmt="pct")
    c.add("cfo_debt", "Cash from operations / lease-adjusted debt", "%", all="=%s/{adj_debt}" % S("cfo"), fmt="pct")
    c.section("Altman Z'")
    c.add("z", "Z' score", "x", all=z_formula(S("operating_income")), fmt="0.00")
    c.add("zone", "Zone", "", all='=IF({z}<%s,"Distress",IF({z}<%s,"Grey","Safe"))' % (I("z_distress"), I("z_safe")), fmt="text")
    c.section("Scorecard")
    scorecard("", "leverage", "coverage", "z")
    c.section("Covenant headroom (EBITDA that can be lost before a breach)")
    c.add("lev_cushion", "  Leverage covenant", "%", all="=1-{adj_debt}/(%s*{ebitda})" % I("max_lev"), fmt="pct")
    c.add("cov_cushion", "  Coverage covenant", "%", all="=1-%s*{interest}/{ebitda}" % I("min_cov"), fmt="pct")
    c.add("cushion", "  Binding headroom", "%", all="=MIN({lev_cushion},{cov_cushion})", fmt="pct")
    c.section("Debt capacity (additional lease-adjusted debt; negative = over capacity)")
    c.add("cap_leverage", "  At target leverage", "$m", all="=%s*{ebitda}-{adj_debt}" % I("cap_lev"), fmt="m")
    c.add("cap_coverage", "  At minimum coverage", "$m", all="=({ebitda}/%s-{interest})/%s" % (I("cap_cov"), I("cap_rate")), fmt="m")
    c.add("capacity", "  Capacity (lower of the two)", "$m", all="=MIN({cap_leverage},{cap_coverage})", style="total", fmt="m")

    # ---------------------------------------------------------------- Stress
    t = m.sheet("Stress", "Stress: EBITDA down and rates up on floating debt; rating migration and covenant breaches")
    t.cell("A5", "Borrower")
    C = lambda k: "{Credit.%s}" % k
    t.add("s_ebitda", "Stressed EBITDA", "$m", all="=%s*(1-%s)" % (C("ebitda"), I("shock")), fmt="m")
    t.add("s_interest", "Stressed interest", "$m", all="=%s+%s*%s*%s" % (C("interest"), I("rate_shock"), I("floating"), S("debt")), fmt="m")
    t.add("s_leverage", "Stressed leverage", "x", all="=%s/{s_ebitda}" % C("adj_debt"), fmt="x")
    t.add("s_coverage", "Stressed coverage", "x", all="={s_ebitda}/{s_interest}", fmt="x")
    t.add("s_z", "Stressed Z' (EBIT reduced by the EBITDA loss)", "x",
          all=z_formula("(%s-%s*%s)" % (S("operating_income"), I("shock"), C("ebitda"))), fmt="0.00")
    t.add("s_lev_band", "  Leverage band", "band", all="=1+SUMPRODUCT((%s<{s_leverage})*1)" % rng("levb"), fmt="n")
    t.add("s_cov_band", "  Coverage band", "band", all="=1+SUMPRODUCT((%s>{s_coverage})*1)" % rng("covb"), fmt="n")
    t.add("s_idx", "  Rating band", "band", all="=MIN(%s,ROUND(%s*{s_lev_band}+(1-%s)*{s_cov_band},0)+IF({s_z}<%s,%s,0))" % (
        I("n_bands"), I("lev_w"), I("lev_w"), I("z_distress"), I("notches")), fmt="n")
    t.add("s_rating", "  Stressed rating", "", all="=INDEX(%s,{s_idx})" % rng("rating"), fmt="text")
    t.add("s_pd", "  Stressed one-year PD", "%", all="=INDEX(%s,{s_idx})" % rng("pd"), fmt="0.00%")
    t.add("notches", "Notches of downgrade", "count", all="={s_idx}-%s" % C("idx"), fmt="n")
    t.add("s_breach", "Covenant breach under stress (1 = yes)", "flag",
          all="=IF(OR({s_leverage}>%s,{s_coverage}<%s),1,0)" % (I("max_lev"), I("min_cov")), fmt="flag")
    t.add("n_breach", "Borrowers breaching under stress", "count", const="=SUM({s_breach:all})", fmt="n")

    # ---------------------------------------------------------------- Checks
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)")
    checks = [
        ("bs_tie", "Each borrower's balance sheet balances", "=SUMPRODUCT(ABS({Spreads.bs_tie:all}))"),
        ("band_range", "Every rating band within the grid", "=SUMPRODUCT(({Credit.idx:all}<1)+({Credit.idx:all}>%s))" % I("n_bands")),
        ("pd_order", "PDs rise with every band", "=SUMPRODUCT((%s:%s>=%s:%s)*1)" % (I("pd_1"), I(f"pd_{nR - 1}"), I("pd_2"), I(f"pd_{nR}"))),
        ("stress_dir", "Stress never improves a rating", "=SUMPRODUCT(({Stress.notches:all}<0)*1)"),
    ]
    for key, label, f in checks:
        ck.add(key, label, "", const=f, style="check")
    ck.blank()
    ck.add("tolerance", "Tolerance", "$m", const=0.001, fmt="0.000")
    ck.add("master", "MASTER CHECK (0 = all pass)", "count",
           const="=IF(SUMPRODUCT(ABS({$%s}:{$%s}))<{$tolerance},0,1)" % (checks[0][0], checks[-1][0]), style="total", fmt="flag")
    m.names["MasterCheck"] = f"'Checks'!$C${ck.row('master')}"
