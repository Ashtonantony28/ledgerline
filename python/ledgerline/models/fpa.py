"""Workbook 06: FP&A budget, 9+3 rolling forecast, variance bridges, forecast accuracy (docs/models/fpa.md).

Monthly timeline: actual months (blue, from the GL export) then the rolling forecast. The budget runs over the
same columns and is zero outside the budget year (the in-budget flag), so every row keeps one formula.
"""
from __future__ import annotations

import calendar
from datetime import date

from ..build.grid import Model, Timeline

PRODUCTS = ["Core", "Premium", "Services"]
DEPTS = ["SalesMarketing", "Operations", "GA"]
DEPT_LABEL = {"SalesMarketing": "Sales and marketing", "Operations": "Operations", "GA": "General and administrative"}
CASES = ["base", "upside", "downside"]
CASE_LABEL = {"base": "Base", "upside": "Upside", "downside": "Downside"}
J = "Judgement (synthetic group): see spec/FPA.yaml for the rationale."
W05 = "Workbook 05 (05_Group_Close.xlsx), FY2025 consolidated statements; embedded as a value (ADR 0003, no external links)."
GL = "GL export fixtures/fpa/actuals.csv (seeded generator python/ledgerline/data/fpa.py); Power Query script powerquery/Actuals.pq."


def timeline(g: dict) -> Timeline:
    cal = g["spec"]["calendar"]
    y, mth = (int(x) for x in str(cal["start"]).split("-"))
    ends, labels = [], []
    for t in range(cal["n_actual"] + cal["n_forecast"]):
        yy, mm = y + (mth - 1 + t) // 12, (mth - 1 + t) % 12 + 1
        ends.append(date(yy, mm, calendar.monthrange(yy, mm)[1]).isoformat())
        labels.append(f"{calendar.month_abbr[mm]}-{yy % 100:02d}")
    return Timeline(ends, labels, cal["n_actual"])


def add_fpa(m: Model, g: dict, scenario: int = 1) -> None:
    s, act = g["spec"], g["act"]
    cal, py, b, fc, fin = s["calendar"], s["prior_year"], s["budget"], s["forecast"], s["finance"]
    tl = m.timeline
    nh, nf, T = tl.n_hist, tl.n - tl.n_hist, tl.n
    lb = cal["lookback"]
    w0, w1 = nh - lb, nh - 1            # run-rate window (timeline columns)
    b0, b1 = 0, cal["budget_months"] - 1  # budget year
    I = lambda k: "{Inputs.$%s}" % k
    blankf = [None] * nf

    # ---------------------------------------------------------------- Inputs
    s_ = m.sheet("Inputs", "Inputs: switches, prior-year anchors (workbook 05), budget and forecast assumptions")
    s_.section("Switches")
    s_.add("scenario", "Forecast case (1 Base, 2 Upside, 3 Downside)", "count", const=scenario, fmt="n")
    s_.add("scenario_name", "Forecast case name", "", const='=CHOOSE({$scenario},"Base","Upside","Downside")', fmt="text")
    s_.blank()
    s_.section("Calendar")
    s_.add("months_in_year", "Months in a year", "count", const=12, fmt="n", const_note="Calendar constant.")
    s_.add("budget_months", "Budget year length from the first timeline month", "count", const=cal["budget_months"], fmt="n",
           const_note="FY2026 = Jan-Dec 2026, the first twelve timeline months.")
    s_.blank()
    s_.section("Prior year, FY2025 (workbook 05)")
    s_.add("py_revenue", "Consolidated revenue", "$m", const=py["revenue"], fmt="m1", const_note=W05 + " Statements: revenue.")
    s_.add("py_dep", "Consolidated depreciation", "$m", const=py["dep_annual"], fmt="m1", const_note=W05 + " Statements: depreciation.")
    s_.add("py_nwc", "Net working capital (receivables + inventory - payables)", "$m", const=py["nwc"], fmt="m1",
           const_note=W05 + " Statements: 202.073 + 204.321 - 100.079.")
    s_.add("py_cash", "Cash at 31 Dec 2025", "$m", const=py["cash"], fmt="m1", const_note=W05 + " Statements: cash.")
    s_.add("nwc_pct", "Net working capital % of annual revenue", "%", const="={$py_nwc}/{$py_revenue}", fmt="pct")
    s_.blank()
    s_.section("Products (FY2025 split: judgement, the split is not in workbook 05)")
    for p in PRODUCTS:
        pr = s["products"][p]
        s_.add(f"share_{p}", f"{p}: share of FY2025 revenue", "%", const=pr["share"], fmt="pct", const_note=J)
        s_.add(f"pyprice_{p}", f"{p}: FY2025 price", "$/unit", const=pr["price"], fmt="ps", const_note=J)
        s_.add(f"pyuc_{p}", f"{p}: FY2025 unit cost", "$/unit", const=pr["unit_cost"], fmt="ps", const_note=J)
        s_.add(f"pyvol_{p}", f"{p}: FY2025 volume", "m units", const="={$share_%s}*{$py_revenue}/{$pyprice_%s}" % (p, p), fmt="n1")
    s_.add("share_sum", "Shares sum", "%", const="=" + "+".join("{$share_%s}" % p for p in PRODUCTS), fmt="pct")
    s_.blank()
    s_.section("FY2026 budget (judgement)")
    for p in PRODUCTS:
        s_.add(f"bg_{p}", f"{p}: volume growth", "%", const=b["volume_growth"][p], fmt="pct", const_note=J)
        s_.add(f"bpi_{p}", f"{p}: price increase", "%", const=b["price_increase"][p], fmt="pct", const_note=J)
        s_.add(f"bci_{p}", f"{p}: unit cost inflation", "%", const=b["cost_inflation"][p], fmt="pct", const_note=J)
    for k, w in enumerate(b["seasonality"], 1):
        s_.add(f"season_{k}", f"Seasonality: {calendar.month_abbr[k]}", "% of year", const=w, fmt="pct", const_note=J)
    for d in DEPTS:
        dd = b["departments"][d]
        s_.add(f"heads_open_{d}", f"{DEPT_LABEL[d]}: heads at 31 Dec 2025", "people", const=dd["heads_open"], fmt="n", const_note=J)
        s_.add(f"cph_{d}", f"{DEPT_LABEL[d]}: FY2025 cost per head", "$m/yr", const=dd["cost_per_head"], fmt="0.000", const_note=J)
    s_.add("pay_raise", "Pay rise from January", "%", const=b["pay_raise"], fmt="pct", const_note=J)
    s_.add("sm_np_pct", "Sales and marketing programme spend, % of revenue", "%", const=b["sm_nonpeople_pct"], fmt="pct", const_note=J)
    s_.add("ops_np", "Operations non-people cost", "$m/yr", const=b["ops_nonpeople"], fmt="m1", const_note=J)
    s_.add("ga_np", "G&A non-people cost", "$m/yr", const=b["ga_nonpeople"], fmt="m1", const_note=J)
    s_.add("bcapex", "Capex per month", "$m", const=b["capex_month"], fmt="m1", const_note=J)
    s_.blank()
    s_.section("Rolling forecast (judgement)")
    for p in PRODUCTS:
        s_.add(f"fci_{p}", f"{p}: unit cost inflation per month", "%", const=fc["cost_inflation_month"][p], fmt="0.00%", const_note=J)
    s_.add("wage_m", "Wage inflation per month", "%", const=fc["wage_inflation_month"], fmt="0.00%", const_note=J)
    s_.add("fcapex", "Capex per month", "$m", const=fc["capex_month"], fmt="m1", const_note=J)
    s_.add("lookback", "Run-rate window (last actual months)", "count", const=lb, fmt="n",
           const_note="Judgement: three months smooths noise but still reacts to the May volume break.")
    s_.blank()
    s_.section("Finance")
    s_.add("tax", "Tax rate", "%", const=fin["tax_rate"], fmt="pct", const_note=J)
    s_.add("life_new", "Life of new capex", "months", const=fin["life_new_months"], fmt="n", const_note=J)
    s_.add("min_cash", "Minimum cash (treasury policy)", "$m", const=fin["min_cash"], fmt="m1", const_note=J)
    s_.blank()
    s_.section("Budget headcount plan: net hires per month (judgement)")
    for d in DEPTS:
        hires = b["departments"][d]["hires"]
        r = s_.add(f"bhires_{d}", f"  {DEPT_LABEL[d]}", "people", all=list(hires) + [None] * (T - len(hires)),
                   style="input", fmt="n")
        r.note = J

    # ---------------------------------------------------------------- Actuals (GL export, as ingested)
    a = m.sheet("Actuals", "Actuals: monthly GL export (seeded synthetic ledger), ingested by Power Query in Excel")
    for p in PRODUCTS:
        a.section(p)
        for acct, label, unit, fmt in (("volume", "Volume", "m units", "0.0000"), ("revenue", "Revenue", "$m", "m1"),
                                       ("cogs", "Cost of goods sold", "$m", "m1")):
            r = a.add(f"{acct}_{p}", f"  {label}", unit, hist=act[(acct, p)] + blankf, style="input", fmt=fmt)
            r.note = GL
    for d in DEPTS:
        a.section(DEPT_LABEL[d])
        for acct, label, unit, fmt in (("heads", "Headcount", "people", "n"), ("people_cost", "People cost", "$m", "m1"),
                                       ("nonpeople_cost", "Non-people cost", "$m", "m1")):
            r = a.add(f"{acct}_{d}", f"  {label}", unit, hist=act[(acct, d)] + blankf, style="input", fmt=fmt)
            r.note = GL
    a.section("Group")
    r = a.add("capex", "  Capex", "$m", hist=act[("capex", "Group")] + blankf, style="input", fmt="m1"); r.note = GL
    r = a.add("gl_revenue", "  GL control total: revenue", "$m", hist=act[("gl_revenue", "Group")] + blankf, style="input", fmt="m1"); r.note = GL
    r = a.add("gl_opex", "  GL control total: operating expenses", "$m", hist=act[("gl_opex", "Group")] + blankf, style="input", fmt="m1"); r.note = GL
    a.add("tie_revenue", "Product revenue less GL control", "$m", hist="=" + "+".join("{revenue_%s}" % p for p in PRODUCTS) + "-{gl_revenue}",
          fmt="m1")
    a.add("tie_opex", "Department opex less GL control", "$m",
          hist="=" + "+".join("{people_cost_%s}+{nonpeople_cost_%s}" % (d, d) for d in DEPTS) + "-{gl_opex}", fmt="m1")

    # ---------------------------------------------------------------- Scenarios (forecast cases)
    sc = m.sheet("Scenarios", "Rolling-forecast cases: volume growth on the run-rate, price change, net hires")
    for p in PRODUCTS:
        for drv, label in (("growth", "volume growth per month"), ("price", "price change per month")):
            sc.section(f"{p}: {label}")
            for case in CASES:
                r = sc.add(f"{drv}_{p}_{case}", f"  {CASE_LABEL[case]}", "%", fcst=[None] * nh + [fc["scenarios"][case][drv][p]] * nf,
                           style="input", fmt="0.00%")
                r.note = J
    for d in DEPTS:
        sc.section(f"{DEPT_LABEL[d]}: net hires per month")
        for case in CASES:
            r = sc.add(f"hires_{d}_{case}", f"  {CASE_LABEL[case]}", "people", fcst=[None] * nh + [fc["scenarios"][case]["hires"][d]] * nf,
                       style="input", fmt="n")
            r.note = J

    # ---------------------------------------------------------------- Drivers (live)
    dv = m.sheet("Drivers", "Live drivers: actual months from the GL, forecast months from run-rates and the selected case")
    dv.section("Calendar")
    dv.add("seq", "Month number on the timeline", "count", hist=[1] + ["={seq@-1}+1"] * (nh - 1), fcst="={seq@-1}+1", fmt="n")
    dv.add("month_idx", "Month of year", "count", hist=[1] + ["=MOD({month_idx@-1},%s)+1" % I("months_in_year")] * (nh - 1),
           fcst="=MOD({month_idx@-1},%s)+1" % I("months_in_year"), fmt="n")
    dv.add("in_budget", "In budget year (1 = yes)", "flag", all="=IF({seq}<=%s,1,0)" % I("budget_months"), fmt="flag")
    dv.add("seas", "Seasonality weight", "%", all="=INDEX(%s:%s,{month_idx})" % (I("season_1"), I("season_12")), fmt="pct")
    for p in PRODUCTS:
        dv.section(p)
        dv.add(f"rr_{p}", "  Deseasonalised run-rate volume (last actual months)", "m units/yr",
               const="=SUM({vol_%s#%d:%d})/SUM({seas#%d:%d})" % (p, w0, w1, w0, w1), fmt="n1")
        dv.add(f"g_{p}", "  Volume growth per month (live case)", "%", fcst="=CHOOSE(%s,%s)" % (
            I("scenario"), ",".join("{Scenarios.growth_%s_%s}" % (p, c) for c in CASES)), fmt="0.00%")
        dv.add(f"gi_{p}", "  Growth index (actual months = 1)", "x", hist=[1] * nh, fcst="={gi_%s@-1}*(1+{g_%s})" % (p, p), fmt="0.0000")
        dv.add(f"vol_{p}", "  Volume", "m units", hist="={Actuals.volume_%s}" % p, fcst="={$rr_%s}*{seas}*{gi_%s}" % (p, p), fmt="0.0000")
        dv.add(f"infl_{p}", "  Price change per month (live case)", "%", fcst="=CHOOSE(%s,%s)" % (
            I("scenario"), ",".join("{Scenarios.price_%s_%s}" % (p, c) for c in CASES)), fmt="0.00%")
        dv.add(f"price_{p}", "  Price (actual = realised)", "$/unit", hist="={Actuals.revenue_%s}/{Actuals.volume_%s}" % (p, p),
               fcst="={price_%s@-1}*(1+{infl_%s})" % (p, p), fmt="ps")
        dv.add(f"uc_{p}", "  Unit cost (actual = realised)", "$/unit", hist="={Actuals.cogs_%s}/{Actuals.volume_%s}" % (p, p),
               fcst="={uc_%s@-1}*(1+%s)" % (p, I(f"fci_{p}")), fmt="ps")
    dv.add("rev_link", "Revenue (from PnL, for the run-rate window)", "$m", all="={PnL.rev}", fmt="m1")
    for d in DEPTS:
        dv.section(DEPT_LABEL[d])
        dv.add(f"hires_{d}", "  Net hires per month (live case)", "people", fcst="=CHOOSE(%s,%s)" % (
            I("scenario"), ",".join("{Scenarios.hires_%s_%s}" % (d, c) for c in CASES)), fmt="n")
        dv.add(f"heads_{d}", "  Headcount", "people", hist="={Actuals.heads_%s}" % d, fcst="={heads_%s@-1}+{hires_%s}" % (d, d), fmt="n")
        dv.add(f"cph_{d}", "  Cost per head per month", "$m", hist="={Actuals.people_cost_%s}/{Actuals.heads_%s}" % (d, d),
               fcst="={cph_%s@-1}*(1+%s)" % (d, I("wage_m")), fmt="0.00000")
        if d == "SalesMarketing":
            dv.add("np_sm_pct", "  Programme spend % of revenue (run-rate)", "%",
                   const="=SUM({np_%s#%d:%d})/SUM({rev_link#%d:%d})" % (d, w0, w1, w0, w1), fmt="pct")
            dv.add(f"np_{d}", "  Non-people cost", "$m", hist="={Actuals.nonpeople_cost_%s}" % d, fcst="={$np_sm_pct}*{rev_link}", fmt="m1")
        else:
            dv.add(f"np_rr_{d}", "  Non-people run-rate per month", "$m", const="=AVERAGE({np_%s#%d:%d})" % (d, w0, w1), fmt="m1")
            dv.add(f"np_{d}", "  Non-people cost", "$m", hist="={Actuals.nonpeople_cost_%s}" % d, fcst="={$np_rr_%s}" % d, fmt="m1")
    dv.section("Capex")
    dv.add("capex", "Capex", "$m", hist="={Actuals.capex}", fcst="=%s" % I("fcapex"), fmt="m1")

    # ---------------------------------------------------------------- Budget
    bu = m.sheet("Budget", "FY2026 budget: prior-year anchors x drivers x seasonality (zero outside the budget year)")
    F = "{Drivers.in_budget}"
    for p in PRODUCTS:
        bu.section(p)
        bu.add(f"bvol_{p}", "  Volume", "m units", all="=%s*(1+%s)*{Drivers.seas}*%s" % (I(f"pyvol_{p}"), I(f"bg_{p}"), F), fmt="0.0000")
        bu.add(f"bprice_{p}", "  Price", "$/unit", all="=%s*(1+%s)*%s" % (I(f"pyprice_{p}"), I(f"bpi_{p}"), F), fmt="ps")
        bu.add(f"buc_{p}", "  Unit cost", "$/unit", all="=%s*(1+%s)*%s" % (I(f"pyuc_{p}"), I(f"bci_{p}"), F), fmt="ps")
        bu.add(f"brev_{p}", "  Revenue", "$m", all="={bvol_%s}*{bprice_%s}" % (p, p), fmt="m1")
        bu.add(f"bcogs_{p}", "  Cost of goods sold", "$m", all="={bvol_%s}*{buc_%s}" % (p, p), fmt="m1")
    bu.section("Budget P&L")
    bu.add("brev", "Revenue", "$m", all="=" + "+".join("{brev_%s}" % p for p in PRODUCTS), style="total", fmt="m1")
    bu.add("bcogs", "Cost of goods sold", "$m", all="=" + "+".join("{bcogs_%s}" % p for p in PRODUCTS), fmt="m1")
    bu.add("bgp", "Gross profit", "$m", all="={brev}-{bcogs}", style="total", fmt="m1")
    for d in DEPTS:  # opening heads + cumulative hires (the SUM range grows with the column)
        hr = s_.row(f"bhires_{d}")
        bu.add(f"bheads_{d}", f"{DEPT_LABEL[d]}: headcount", "people", fmt="n",
               all=lambda i, d=d, hr=hr: "=%s+SUM('Inputs'!$%s$%d:%s%d)" % (I(f"heads_open_{d}"), tl.col(0), hr, tl.col(i), hr))
    for d in DEPTS:
        bu.add(f"bpeople_{d}", f"{DEPT_LABEL[d]}: people cost", "$m",
               all="={bheads_%s}*%s*(1+%s)/%s*%s" % (d, I(f"cph_{d}"), I("pay_raise"), I("months_in_year"), F), fmt="m1")
    bu.add("bnp_SalesMarketing", "Sales and marketing: non-people cost", "$m", all="=%s*{brev}" % I("sm_np_pct"), fmt="m1")
    bu.add("bnp_Operations", "Operations: non-people cost", "$m", all="=%s/%s*%s" % (I("ops_np"), I("months_in_year"), F), fmt="m1")
    bu.add("bnp_GA", "G&A: non-people cost", "$m", all="=%s/%s*%s" % (I("ga_np"), I("months_in_year"), F), fmt="m1")
    for d in DEPTS:
        bu.add(f"bopex_{d}", f"{DEPT_LABEL[d]}: operating expenses", "$m", all="={bpeople_%s}+{bnp_%s}" % (d, d), fmt="m1")
    bu.add("bopex", "Operating expenses", "$m", all="=" + "+".join("{bopex_%s}" % d for d in DEPTS), style="total", fmt="m1")
    bu.add("bebitda", "EBITDA", "$m", all="={bgp}-{bopex}", style="total", fmt="m1")
    bu.add("bcapex", "Capex", "$m", all="=%s*%s" % (I("bcapex"), F), fmt="m1")
    bu.add("bvol_year", "Budget-year volume check: sum of months less FY2025 x (1 + growth)", "m units", fmt="0.0000",
           const="=" + "+".join("ABS(SUM({bvol_%s#%d:%d})-%s*(1+%s))" % (p, b0, b1, I(f"pyvol_{p}"), I(f"bg_{p}")) for p in PRODUCTS))

    # ---------------------------------------------------------------- PnL: actual + forecast, cash
    pl = m.sheet("PnL", "Outlook: actual months then rolling forecast; P&L, cash flow and cash")
    for p in PRODUCTS:
        pl.add(f"rev_{p}", f"Revenue: {p}", "$m", all="={Drivers.vol_%s}*{Drivers.price_%s}" % (p, p), fmt="m1")
    pl.add("rev", "Revenue", "$m", all="=" + "+".join("{rev_%s}" % p for p in PRODUCTS), style="total", fmt="m1")
    for p in PRODUCTS:
        pl.add(f"cogs_{p}", f"Cost of goods sold: {p}", "$m", all="={Drivers.vol_%s}*{Drivers.uc_%s}" % (p, p), fmt="m1")
    pl.add("cogs", "Cost of goods sold", "$m", all="=" + "+".join("{cogs_%s}" % p for p in PRODUCTS), fmt="m1")
    pl.add("gp", "Gross profit", "$m", all="={rev}-{cogs}", style="total", fmt="m1")
    pl.add("gm", "Gross margin", "%", all="={gp}/{rev}", fmt="pct")
    for d in DEPTS:
        pl.add(f"people_{d}", f"{DEPT_LABEL[d]}: people cost", "$m", all="={Drivers.heads_%s}*{Drivers.cph_%s}" % (d, d), fmt="m1")
        pl.add(f"np_{d}", f"{DEPT_LABEL[d]}: non-people cost", "$m", all="={Drivers.np_%s}" % d, fmt="m1")
        pl.add(f"opex_{d}", f"{DEPT_LABEL[d]}: operating expenses", "$m", all="={people_%s}+{np_%s}" % (d, d), fmt="m1")
    pl.add("opex", "Operating expenses", "$m", all="=" + "+".join("{opex_%s}" % d for d in DEPTS), style="total", fmt="m1")
    pl.add("ebitda", "EBITDA", "$m", all="={gp}-{opex}", style="total", fmt="m1")
    pl.add("capex", "Capex", "$m", all="={Drivers.capex}", fmt="m1")
    pl.add("dep", "Depreciation: FY2025 run-rate + new capex straight line", "$m",
           all=lambda i: "=%s/%s+SUM($%s$%d:%s%d)/%s" % (I("py_dep"), I("months_in_year"), tl.col(0), pl.row("capex"),
                                                        tl.col(i), pl.row("capex"), I("life_new")), fmt="m1")
    pl.add("ebit", "Operating profit", "$m", all="={ebitda}-{dep}", fmt="m1")
    pl.add("tax", "Cash tax", "$m", all="=%s*MAX(0,{ebit})" % I("tax"), fmt="m1")
    pl.add("nwc", "Net working capital (% of annualised revenue)", "$m", all="=%s*{rev}*%s" % (I("nwc_pct"), I("months_in_year")), fmt="m1")
    pl.add("nwc_prev", "Net working capital, previous month", "$m", hist=[py["nwc"]] + ["={nwc@-1}"] * (nh - 1), fcst="={nwc@-1}", fmt="m1",
           note=W05 + " First month: FY2025 closing net working capital.")
    pl.add("dnwc", "Increase in net working capital", "$m", all="={nwc}-{nwc_prev}", fmt="m1")
    pl.add("fcf", "Free cash flow", "$m", all="={ebitda}-{tax}-{dnwc}-{capex}", style="total", fmt="m1")
    pl.add("cash_open", "Cash, opening", "$m", hist=[py["cash"]] + ["={cash@-1}"] * (nh - 1), fcst="={cash@-1}", fmt="m1",
           note=W05 + " First month: FY2025 closing cash.")
    pl.add("cash", "Cash, closing", "$m", all="={cash_open}+{fcf}", style="total", fmt="m1")
    pl.blank()
    pl.add("min_cash_fc", "Lowest forecast cash", "$m", const="=MIN({cash:fcst})", fmt="m1")
    pl.add("min_cash_month", "Month of lowest forecast cash", "", const="=INDEX({fy:fcst},MATCH({$min_cash_fc},{cash:fcst},0))", fmt="text")
    pl.add("headroom", "Headroom over minimum cash", "$m", const="={$min_cash_fc}-%s" % I("min_cash"), fmt="m1")
    pl.add("fy_rev", "FY2026 outlook: revenue (actual + forecast)", "$m", const="=SUM({rev#%d:%d})" % (b0, b1), fmt="m1")
    pl.add("fy_ebitda", "FY2026 outlook: EBITDA", "$m", const="=SUM({ebitda#%d:%d})" % (b0, b1), fmt="m1")

    # ---------------------------------------------------------------- Variance
    va = m.sheet("Variance", "Budget vs actual and outlook: monthly variances and price / volume / mix bridges")
    va.add("var_rev", "Revenue variance (outlook - budget, budget year)", "$m", all="=({PnL.rev}-{Budget.brev})*%s" % F, fmt="m1")
    va.add("var_gp", "Gross profit variance", "$m", all="=({PnL.gp}-{Budget.bgp})*%s" % F, fmt="m1")
    va.add("var_opex", "Operating expense variance (+ = overspend)", "$m", all="=({PnL.opex}-{Budget.bopex})*%s" % F, fmt="m1")
    va.add("var_ebitda", "EBITDA variance", "$m", all="=({PnL.ebitda}-{Budget.bebitda})*%s" % F, fmt="m1")
    for scope, (lo, hi), title in (("ytd", (0, nh - 1), "Year to date (actual months)"),
                                   ("fy", (b0, b1), "Full year FY2026 (actual + forecast)")):
        R = lambda sheet, key: "SUM({%s.%s#%d:%d})" % (sheet, key, lo, hi)
        k = lambda name: f"{scope}_{name}"
        va.blank()
        va.section(title)
        for p in PRODUCTS:
            va.add(k(f"av_{p}"), f"{p}: actual volume", "m units", const="=" + R("Drivers", f"vol_{p}"), fmt="n1")
            va.add(k(f"ar_{p}"), f"{p}: actual revenue", "$m", const="=" + R("PnL", f"rev_{p}"), fmt="m1")
            va.add(k(f"ac_{p}"), f"{p}: actual COGS", "$m", const="=" + R("PnL", f"cogs_{p}"), fmt="m1")
            va.add(k(f"bv_{p}"), f"{p}: budget volume", "m units", const="=" + R("Budget", f"bvol_{p}"), fmt="n1")
            va.add(k(f"br_{p}"), f"{p}: budget revenue", "$m", const="=" + R("Budget", f"brev_{p}"), fmt="m1")
            va.add(k(f"bc_{p}"), f"{p}: budget COGS", "$m", const="=" + R("Budget", f"bcogs_{p}"), fmt="m1")
        c = lambda name: "{$%s}" % k(name)
        va.add(k("avt"), "Total actual volume", "m units", const="=" + "+".join(c(f"av_{p}") for p in PRODUCTS), fmt="n1")
        va.add(k("bvt"), "Total budget volume", "m units", const="=" + "+".join(c(f"bv_{p}") for p in PRODUCTS), fmt="n1")
        va.add(k("rev_actual"), "Actual revenue", "$m", const="=" + "+".join(c(f"ar_{p}") for p in PRODUCTS), fmt="m1")
        va.add(k("rev_budget"), "Budget revenue", "$m", const="=" + "+".join(c(f"br_{p}") for p in PRODUCTS), fmt="m1")
        va.add(k("bgp"), "Budget gross profit", "$m", const="={$%s}-(%s)" % (k("rev_budget"), "+".join(c(f"bc_{p}") for p in PRODUCTS)), fmt="m1")
        va.add(k("price"), "Price variance: sum of actual volume x (actual - budget price)", "$m",
               const="=" + "+".join("(%s-%s*%s/%s)" % (c(f"ar_{p}"), c(f"av_{p}"), c(f"br_{p}"), c(f"bv_{p}")) for p in PRODUCTS), style="total", fmt="m1")
        va.add(k("rev_volume"), "Volume variance at budget mix and price", "$m",
               const="=(%s-%s)*%s/%s" % (c("avt"), c("bvt"), c("rev_budget"), c("bvt")), style="total", fmt="m1")
        va.add(k("rev_mix"), "Mix variance at budget price", "$m",
               const="=" + "+".join("%s*%s/%s" % (c(f"av_{p}"), c(f"br_{p}"), c(f"bv_{p}")) for p in PRODUCTS)
               + "-%s*%s/%s" % (c("avt"), c("rev_budget"), c("bvt")), style="total", fmt="m1")
        va.add(k("cost"), "Unit cost variance (+ = favourable)", "$m",
               const="=-(" + "+".join("(%s-%s*%s/%s)" % (c(f"ac_{p}"), c(f"av_{p}"), c(f"bc_{p}"), c(f"bv_{p}")) for p in PRODUCTS) + ")",
               style="total", fmt="m1")
        va.add(k("gp_volume"), "Volume variance at budget unit margin", "$m",
               const="=(%s-%s)*%s/%s" % (c("avt"), c("bvt"), c("bgp"), c("bvt")), style="total", fmt="m1")
        va.add(k("gp_mix"), "Mix variance at budget unit margin", "$m",
               const="=" + "+".join("%s*(%s-%s)/%s" % (c(f"av_{p}"), c(f"br_{p}"), c(f"bc_{p}"), c(f"bv_{p}")) for p in PRODUCTS)
               + "-%s*%s/%s" % (c("avt"), c("bgp"), c("bvt")), style="total", fmt="m1")
        for d in DEPTS:
            va.add(k(f"ahm_{d}"), f"{DEPT_LABEL[d]}: actual head-months", "people", const="=" + R("Drivers", f"heads_{d}"), fmt="n")
            va.add(k(f"bhm_{d}"), f"{DEPT_LABEL[d]}: budget head-months", "people",
                   const="=SUMPRODUCT({Budget.bheads_%s#%d:%d},{Drivers.in_budget#%d:%d})" % (d, lo, hi, lo, hi), fmt="n")
            va.add(k(f"bcph_{d}"), f"{DEPT_LABEL[d]}: budget cost per head-month", "$m",
                   const="=%s/%s" % (R("Budget", f"bpeople_{d}"), c(f"bhm_{d}")), fmt="0.00000")
            va.add(k(f"heads_{d}"), f"{DEPT_LABEL[d]}: headcount variance (+ = overspend)", "$m",
                   const="=(%s-%s)*%s" % (c(f"ahm_{d}"), c(f"bhm_{d}"), c(f"bcph_{d}")), fmt="m1")
            va.add(k(f"rate_{d}"), f"{DEPT_LABEL[d]}: pay-rate variance", "$m",
                   const="=%s-%s*%s" % (R("PnL", f"people_{d}"), c(f"ahm_{d}"), c(f"bcph_{d}")), fmt="m1")
            va.add(k(f"np_{d}"), f"{DEPT_LABEL[d]}: non-people variance", "$m",
                   const="=%s-%s" % (R("PnL", f"np_{d}"), R("Budget", f"bnp_{d}")), fmt="m1")
        va.add(k("heads"), "Headcount variance", "$m", const="=" + "+".join(c(f"heads_{d}") for d in DEPTS), style="total", fmt="m1")
        va.add(k("rate"), "Pay-rate variance", "$m", const="=" + "+".join(c(f"rate_{d}") for d in DEPTS), style="total", fmt="m1")
        va.add(k("np"), "Non-people variance", "$m", const="=" + "+".join(c(f"np_{d}") for d in DEPTS), style="total", fmt="m1")
        va.add(k("opex_var"), "Operating expense variance", "$m", const="=%s-%s" % (R("PnL", "opex"), R("Budget", "bopex")), fmt="m1")
        va.add(k("ebitda_budget"), "EBITDA bridge: budget", "$m", const="=" + R("Budget", "bebitda"), style="total", fmt="m1")
        va.add(k("ebitda_bridge"), "EBITDA bridge: budget + price + cost + volume + mix - headcount - pay rate - non-people", "$m",
               const="=%s+%s+%s+%s+%s-%s-%s-%s" % (c("ebitda_budget"), c("price"), c("cost"), c("gp_volume"), c("gp_mix"),
                                                     c("heads"), c("rate"), c("np")), fmt="m1")
        va.add(k("ebitda_actual"), "EBITDA bridge: actual / outlook", "$m", const="=" + R("PnL", "ebitda"), style="total", fmt="m1")

    # ---------------------------------------------------------------- Accuracy
    ac = m.sheet("Accuracy", "Forecast accuracy: the forecast made at the June close against what happened")
    prior = g["prior"]
    pv = [prior.get(t + 1) for t in range(T)]
    pm = [t for t in range(T) if pv[t] is not None]
    hm = [t for t in pm if t < nh]
    fm = [t for t in pm if t >= nh]
    r = ac.add("prior", "Revenue forecast at the June close", "$m", all=pv, style="input", fmt="m1")
    r.note = "fixtures/fpa/prior_forecast.csv (seeded generator: Apr-Jun run-rate, June price)."
    ac.add("outlook", "Revenue: actual / current outlook", "$m", all="={PnL.rev}", fmt="m1")
    ac.add("err", "Forecast error (forecast - actual)", "$m", hist=lambda i: "={prior}-{outlook}" if i in hm else None, fmt="m1")
    ac.add("ape", "Absolute percentage error", "%", hist=lambda i: "=ABS({err})/{outlook}" if i in hm else None, fmt="pct")
    ac.add("mape", "Mean absolute percentage error, months with actuals", "%", const="=AVERAGE({ape#%d:%d})" % (hm[0], hm[-1]), fmt="pct")
    ac.add("bias", "Bias: total error / total actual (+ = forecast too high)", "%",
           const="=SUM({err#%d:%d})/SUM({outlook#%d:%d})" % (hm[0], hm[-1], hm[0], hm[-1]), fmt="pct")
    ac.add("q4_change", "Change in the forecast for the remaining months since June", "$m",
           const="=SUM({outlook#%d:%d})-SUM({prior#%d:%d})" % (fm[0], fm[-1], fm[0], fm[-1]), fmt="m1")

    # ---------------------------------------------------------------- Checks
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)")
    checks = [
        ("season", "Seasonality sums to 100%", "=ROUND(SUM(%s:%s)-1,{$dp})" % (I("season_1"), I("season_12"))),
        ("shares", "Product shares sum to 100%", "=ROUND(%s-1,{$dp})" % I("share_sum")),
        ("gl_rev", "Product revenue ties to the GL control total", "=SUMPRODUCT(ABS({Actuals.tie_revenue:hist}))"),
        ("gl_opex", "Department opex ties to the GL control total", "=SUMPRODUCT(ABS({Actuals.tie_opex:hist}))"),
        ("bvol", "Budget volumes phase to the annual plan", "={Budget.$bvol_year}"),
    ]
    for scope in ("ytd", "fy"):
        v = lambda name: "{Variance.$%s_%s}" % (scope, name)
        checks += [
            (f"{scope}_rev", f"Revenue bridge sums to the variance ({scope.upper()})",
             "=%s+%s+%s+%s-%s" % (v("rev_budget"), v("price"), v("rev_volume"), v("rev_mix"), v("rev_actual"))),
            (f"{scope}_opex", f"Opex bridge sums to the variance ({scope.upper()})",
             "=%s+%s+%s-%s" % (v("heads"), v("rate"), v("np"), v("opex_var"))),
            (f"{scope}_ebitda", f"EBITDA bridge sums to the outlook ({scope.upper()})", "=%s-%s" % (v("ebitda_bridge"), v("ebitda_actual"))),
        ]
    checks.append(("cash", "Closing cash = opening cash + cumulative free cash flow",
                   "={PnL.cash#%d}-%s-SUM({PnL.fcf:all})" % (T - 1, I("py_cash"))))
    for key, label, f in checks:
        ck.add(key, label, "", const=f, style="check")
    ck.blank()
    ck.add("dp", "Rounding precision for ratio checks (decimal places)", "count", const=9, fmt="n",
           const_note="ADR 0005: ratios agree to 1e-9.")
    ck.add("tolerance", "Tolerance", "$m", const=0.001, fmt="0.000")
    ck.add("master", "MASTER CHECK (0 = all pass)", "count",
           const="=IF(SUMPRODUCT(ABS({$%s}:{$%s}))<{$tolerance},0,1)" % (checks[0][0], checks[-1][0]), style="total", fmt="flag")
    m.names["MasterCheck"] = f"'Checks'!$C${ck.row('master')}"


def add_dashboard(m: Model) -> None:
    """Headline numbers (links only) and the table the charts read."""
    db = m.sheet("Dashboard", "Dashboard: FY2026 outlook against budget", timeline=False)
    db.col_widths = {"A": 44, "B": 14, "C": 14, "D": 14}
    C = lambda sheet, key: "'%s'!$C$%d" % (sheet, m.sheets[sheet].row(key))
    db.cell("A4", "FY2026", bold=True); db.cell("B4", "Budget", bold=True); db.cell("C4", "Outlook", bold=True)
    db.cell("D4", "Variance", bold=True)
    for r, (label, bk, ok) in enumerate((("Revenue", "fy_rev_budget", "fy_rev_actual"),
                                         ("EBITDA", "fy_ebitda_budget", "fy_ebitda_actual")), start=5):
        db.cell(f"A{r}", label); db.cell(f"B{r}", "=" + C("Variance", bk), fmt="m1"); db.cell(f"C{r}", "=" + C("Variance", ok), fmt="m1")
        db.cell(f"D{r}", f"=C{r}-B{r}", fmt="m1")
    rows = [("Year-to-date revenue variance", "=%s-%s" % (C("Variance", "ytd_rev_actual"), C("Variance", "ytd_rev_budget")), "m1"),
            ("Year-to-date EBITDA variance", "=%s-%s" % (C("Variance", "ytd_ebitda_actual"), C("Variance", "ytd_ebitda_budget")), "m1"),
            ("Lowest forecast cash", "=" + C("PnL", "min_cash_fc"), "m1"),
            ("Month of lowest forecast cash", "=" + C("PnL", "min_cash_month"), "text"),
            ("Headroom over minimum cash", "=" + C("PnL", "headroom"), "m1"),
            ("June forecast: MAPE on Jul-Sep revenue", "=" + C("Accuracy", "mape"), "pct"),
            ("June forecast: bias", "=" + C("Accuracy", "bias"), "pct"),
            ("Live forecast case", "=" + C("Inputs", "scenario_name"), "text")]
    for k, (label, f, fmt) in enumerate(rows, start=8):
        db.cell(f"A{k}", label); db.cell(f"B{k}", f, fmt=fmt)
    db.cell("A18", "FY2026 EBITDA bridge", bold=True); db.cell("B18", "$m", bold=True)
    bridge = [("Budget EBITDA", "+", "fy_ebitda_budget"), ("Price", "+", "fy_price"), ("Unit cost", "+", "fy_cost"),
              ("Volume", "+", "fy_gp_volume"), ("Mix", "+", "fy_gp_mix"), ("Headcount", "-", "fy_heads"),
              ("Pay rate", "-", "fy_rate"), ("Non-people", "-", "fy_np"), ("Outlook EBITDA", "+", "fy_ebitda_actual")]
    for k, (label, sign, key) in enumerate(bridge, start=19):
        db.cell(f"A{k}", label); db.cell(f"B{k}", ("=" if sign == "+" else "=-") + C("Variance", key), fmt="m1")


def add_charts(path, m: Model, budget_months: int = 12) -> None:
    """Native Excel charts on the Dashboard (they read live cells, so they move with the model)."""
    from openpyxl import load_workbook
    from openpyxl.chart import BarChart, LineChart, Reference
    wb = load_workbook(path)
    ws = wb["Dashboard"]
    ws.page_setup.orientation = "landscape"  # one printed page for the model book
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    tl = m.timeline
    first, last = 5, 4 + tl.n
    from openpyxl.chart.series import SeriesLabel
    lc = LineChart()
    lc.title, lc.y_axis.title, lc.height, lc.width = "Monthly revenue: actual / forecast vs budget ($m)", "$m", 8, 18
    for sheet, key, name, hi in (("PnL", "rev", "Actual / forecast", last), ("Budget", "brev", "Budget", first + budget_months - 1)):  # budget months only
        r = m.sheets[sheet].row(key)
        lc.add_data(Reference(wb[sheet], min_col=first, max_col=hi, min_row=r), from_rows=True, titles_from_data=False)
        lc.series[-1].tx = SeriesLabel(v=name)
        lc.series[-1].smooth = False
    lc.set_categories(Reference(wb["PnL"], min_col=first, max_col=last, min_row=5))
    lc.legend.position = "b"
    ws.add_chart(lc, "F3")
    bc = BarChart()
    bc.title, bc.height, bc.width = "FY2026 EBITDA variance to budget, by driver ($m)", 8, 18
    bc.add_data(Reference(ws, min_col=2, min_row=20, max_row=26), titles_from_data=False)
    bc.set_categories(Reference(ws, min_col=1, min_row=20, max_row=26))
    bc.legend = None
    ws.add_chart(bc, "F20")
    wb.save(path)
