"""Workbook 02: DCF, trading comps, sensitivity grids and football field (docs/models/dcf-comps.md).

Added on top of the three-statement sheets, so the valuation is live: change a driver and the
implied price moves. The Python reference is ref/dcf.py.
"""
from __future__ import annotations

from openpyxl.chart import BarChart, Reference
from openpyxl.chart.shapes import GraphicalProperties

from ..build.grid import Model
from .assumptions import Inputs
from .valuation_inputs import ValInputs

COMP_COLS = ["Ticker", "Company", "FY", "Period end", "Price ($)", "Shares (m)", "Market cap", "Debt", "Cash + ST inv.",
             "NCI", "EV", "Revenue", "EBITDA", "Net income", "Diluted EPS ($)", "EV / Revenue", "EV / EBITDA", "P / E"]
FIRST_COMP_ROW = 6
STATS = [("Median", "MEDIAN({r})"), ("Mean", "AVERAGE({r})"), ("High", "MAX({r})"), ("Low", "MIN({r})"),
         ("25th percentile", "QUARTILE({r},1)"), ("75th percentile", "QUARTILE({r},3)")]
GRID_STEPS = 5  # 5 x 5 sensitivity grids, base case in the centre


def valuation_checks() -> list:
    return [
        ("wacc_gt_g", "WACC exceeds terminal growth (Gordon model defined)",
         dict(const="=IF({WACC.$wacc}>{WACC.$terminal_growth},0,1)")),
        ("football_ordered", "Football-field ranges ordered (low <= high)",
         dict(const="=IF(SUMPRODUCT(('Football'!$B$5:$B$9>'Football'!$C$5:$C$9)*1)=0,0,1)")),
    ]


def add_valuation(m: Model, inp: Inputs, v: ValInputs) -> None:
    tl = m.timeline
    lh, lf = inp.n_hist - 1, tl.n - 1  # last history / last forecast column index
    n_c = len(v.comps)

    # ---------------------------------------------------------------- WACC
    w = m.sheet("WACC", "Cost of capital")
    w.section("Cost of equity (CAPM)")
    w.add("rf", "Risk-free rate (10-year Treasury)", "%", const=v.rf, fmt="pct", const_note=v.notes["rf"])
    w.add("erp", "Equity risk premium (implied)", "%", const=v.erp, fmt="pct", const_note=v.notes["erp"])
    w.add("beta_raw", "Raw beta (5y monthly vs S&P 500)", "x", const=v.beta_raw, fmt="0.000", const_note=v.notes["beta_raw"])
    w.add("blume_w", "Blume weight on raw beta", "x", const=v.blume_w, fmt="0.00", const_note=v.notes["blume_weight_raw"])
    w.add("beta_adj", "Adjusted beta", "x", const="={$blume_w}*{$beta_raw}+(1-{$blume_w})", fmt="0.000")
    w.add("ke", "Cost of equity", "%", const="={$rf}+{$beta_adj}*{$erp}", fmt="pct", style="total")
    w.blank()
    w.section("Cost of debt")
    w.add("credit_spread", "Credit spread over Treasury", "%", const=v.credit_spread, fmt="pct", const_note=v.notes["credit_spread"])
    w.add("kd_pre", "Pre-tax cost of debt", "%", const="={$rf}+{$credit_spread}", fmt="pct")
    w.add("marginal_tax", "Marginal tax rate", "%", const=v.marginal_tax, fmt="pct", const_note=v.notes["marginal_tax"])
    w.add("kd", "After-tax cost of debt", "%", const="={$kd_pre}*(1-{$marginal_tax})", fmt="pct", style="total")
    w.blank()
    w.section("Capital structure (market values)")
    w.add("price", "Share price", "$", const="={Inputs.$share_price}", fmt="ps")
    w.add("shares_out", "Shares outstanding (10-K cover)", "m", const=v.shares_out, fmt="m1", const_note=v.notes["shares_out"])
    w.add("mcap", "Market capitalisation", "$m", const="={$price}*{$shares_out}")
    w.add("debt", "Debt (book, last balance sheet)", "$m", const="={BS.debt#%d}+{BS.revolver#%d}" % (lh, lh))
    w.add("wd", "Debt / (debt + equity)", "%", const="={$debt}/({$debt}+{$mcap})", fmt="pct")
    w.add("wacc", "WACC", "%", const="={$ke}*(1-{$wd})+{$kd}*{$wd}", fmt="pct", style="total")
    w.blank()
    w.section("DCF settings")
    w.add("terminal_growth", "Terminal growth (Gordon)", "%", const=v.terminal_growth, fmt="pct", const_note=v.notes["terminal_growth"])
    w.add("midyear_adj", "Mid-year adjustment", "years", const=v.midyear_adj, fmt="0.0", const_note=v.notes["midyear_adj"])
    w.add("years_since_fye", "Years from fiscal year end to price date", "years", const=v.years_since_fye, fmt="0.000",
          const_note=v.notes["years_since_fye"])
    w.add("wacc_step", "Sensitivity step: WACC", "%", const=v.wacc_step, fmt="pct", const_note=v.notes["wacc_step"])
    w.add("growth_step", "Sensitivity step: terminal growth", "%", const=v.growth_step, fmt="pct", const_note=v.notes["growth_step"])
    w.add("multiple_step", "Sensitivity step: exit multiple", "x", const=v.multiple_step, fmt="x", const_note=v.notes["multiple_step"])
    m.names["WACC"] = f"'WACC'!$C${w.row('wacc')}"

    # ---------------------------------------------------------------- Comps (table)
    c = m.sheet("Comps", "Trading comparables (latest fiscal year, not calendarised)", timeline=False)
    c.col_widths = {"A": 9, "B": 30, "C": 8, "D": 11, **{chr(ord("E") + k): 12 for k in range(14)}}
    c.cell("A2", "$m unless stated. EV = market cap + debt - cash and short-term investments + NCI; lease liabilities excluded "
                 "consistently with the DCF. Kroger's SG&A is an extension tag, so its EBITDA comes from EBIT + D&A (ADR 0004).",
           italic=True, color="808080")
    for k, h in enumerate(COMP_COLS):
        c.cell(f"{chr(ord('A') + k)}5", h, bold=True)
    for k, comp in enumerate(v.comps):
        r = FIRST_COMP_ROW + k
        vals = [comp.ticker, comp.name, comp.fy, comp.period_end]
        for j, x in enumerate(vals):
            c.cell(f"{chr(ord('A') + j)}{r}", x)
        numbers = {"E": (comp.price, "ps", comp.sources["price"]), "F": (comp.shares_out, "m1", comp.sources["shares"]),
                   "H": (comp.debt, "m", comp.sources["history"]), "I": (comp.cash, "m", comp.sources["history"]),
                   "J": (comp.nci, "m", comp.sources["history"]), "L": (comp.revenue, "m", comp.sources["history"]),
                   "M": (comp.ebitda, "m", comp.sources["history"] + "; EBITDA = operating income + D&A"),
                   "N": (comp.net_income, "m", comp.sources["history"]), "O": (comp.eps, "ps", comp.sources["history"])}
        for col, (x, fmt, note) in numbers.items():
            c.cell(f"{col}{r}", x, input=True, fmt=fmt, note=note)
        c.cell(f"G{r}", f"=E{r}*F{r}", fmt="m")
        c.cell(f"K{r}", f"=G{r}+H{r}-I{r}+J{r}", fmt="m")
        c.cell(f"P{r}", f"=K{r}/L{r}", fmt="x")
        c.cell(f"Q{r}", f"=K{r}/M{r}", fmt="x")
        c.cell(f"R{r}", f"=E{r}/O{r}", fmt="x")
    last = FIRST_COMP_ROW + n_c - 1
    stat_row0 = last + 2
    for k, (label, f) in enumerate(STATS):
        r = stat_row0 + k
        c.cell(f"B{r}", label, bold=True)
        for col in "PQR":
            c.cell(f"{col}{r}", "=" + f.format(r=f"{col}${FIRST_COMP_ROW}:{col}${last}"), fmt="x", bold=(k == 0))
    med_row, q1_row, q3_row = stat_row0, stat_row0 + 4, stat_row0 + 5
    tr = stat_row0 + len(STATS) + 1
    hist_col = tl.col(lh)
    c.cell(f"A{tr}", inp.ticker, bold=True); c.cell(f"B{tr}", "Target at market (for reference, not in statistics)")
    c.cell(f"E{tr}", "='WACC'!$C$%d" % w.row("price"), fmt="ps")
    c.cell(f"F{tr}", "='WACC'!$C$%d" % w.row("shares_out"), fmt="m1")
    c.cell(f"G{tr}", f"=E{tr}*F{tr}", fmt="m")
    c.cell(f"H{tr}", "='WACC'!$C$%d" % w.row("debt"), fmt="m")
    c.cell(f"I{tr}", f"='BS'!${hist_col}${m.sheets['BS'].row('cash')}+'BS'!${hist_col}${m.sheets['BS'].row('st_investments')}", fmt="m")
    c.cell(f"J{tr}", f"='BS'!${hist_col}${m.sheets['BS'].row('nci_equity')}", fmt="m")
    c.cell(f"K{tr}", f"=G{tr}+H{tr}-I{tr}+J{tr}", fmt="m")
    c.cell(f"L{tr}", f"='IS'!${hist_col}${m.sheets['IS'].row('revenue')}", fmt="m")
    c.cell(f"M{tr}", f"='IS'!${hist_col}${m.sheets['IS'].row('ebitda')}", fmt="m")
    c.cell(f"N{tr}", f"='IS'!${hist_col}${m.sheets['IS'].row('net_income')}", fmt="m")
    c.cell(f"O{tr}", f"=N{tr}/'IS'!${hist_col}${m.sheets['IS'].row('shares_diluted')}", fmt="ps")
    c.cell(f"P{tr}", f"=K{tr}/L{tr}", fmt="x"); c.cell(f"Q{tr}", f"=K{tr}/M{tr}", fmt="x"); c.cell(f"R{tr}", f"=E{tr}/O{tr}", fmt="x")
    comps_cells = {"median_ev_ebitda": f"'Comps'!$Q${med_row}", "q1_ev_ebitda": f"'Comps'!$Q${q1_row}",
                   "q3_ev_ebitda": f"'Comps'!$Q${q3_row}", "q1_pe": f"'Comps'!$R${q1_row}", "q3_pe": f"'Comps'!$R${q3_row}",
                   "ebitda0": f"'Comps'!$M${tr}", "eps0": f"'Comps'!$O${tr}"}

    # ---------------------------------------------------------------- DCF
    d = m.sheet("DCF", "Discounted cash flow (unlevered, mid-year convention)")
    d.section("Unlevered free cash flow (SBC treated as a real expense: not added back)")
    d.add("ebit", "EBIT", "$m", fcst="={IS.operating_income}")
    d.add("tax_rate", "Tax rate on EBIT", "%", fcst="={Drivers.tax_rate}", fmt="pct")
    d.add("taxes", "Taxes on EBIT", "$m", fcst="=-{ebit}*{tax_rate}")
    d.add("nopat", "NOPAT", "$m", fcst="={ebit}+{taxes}", style="total")
    d.add("da", "Plus: D&A", "$m", fcst="={Schedules.da}")
    d.add("capex", "Less: capex", "$m", fcst="=-{Schedules.capex}")
    d.add("change_nwc", "Plus: working-capital cash impact", "$m", fcst="={Schedules.change_nwc}")
    d.add("ufcf", "Unlevered free cash flow", "$m", fcst="={nopat}+{da}+{capex}+{change_nwc}", style="total")
    d.add("period", "Discount period (years)", "years", fcst="={fcst_n}-{WACC.$midyear_adj}", fmt="0.0")
    d.add("df", "Discount factor", "x", fcst="=1/(1+{WACC.$wacc})^{period}", fmt="0.0000")
    d.add("pv", "Present value of UFCF", "$m", fcst="={ufcf}*{df}")
    d.blank()
    d.section("Enterprise to equity value (column C)")
    U, DFN, EB, FN = "{ufcf#%d}" % lf, "{df#%d}" % lf, "{IS.ebitda#%d}" % lf, "{fcst_n#%d}" % lf
    d.add("sum_pv", "Sum of PV of UFCF", "$m", const="=SUM({pv:fcst})")
    d.add("net_debt", "Net debt / (net cash) incl. NCI, last balance sheet", "$m",
          const="={BS.debt#%d}+{BS.revolver#%d}-{BS.cash#%d}-{BS.st_investments#%d}+{BS.nci_equity#%d}" % ((lh,) * 5))
    d.add("roll", "Roll-forward to price date (at cost of equity)", "x", const="=(1+{WACC.$ke})^{WACC.$years_since_fye}", fmt="0.0000")
    d.blank()
    d.section("Perpetuity-growth method")
    d.add("tv_g", "Terminal value", "$m", const=f"={U}*(1+{{WACC.$terminal_growth}})/({{WACC.$wacc}}-{{WACC.$terminal_growth}})")
    d.add("pv_tv_g", "PV of terminal value", "$m", const=f"={{$tv_g}}*{DFN}")
    d.add("ev_g", "Enterprise value", "$m", const="={$sum_pv}+{$pv_tv_g}", style="total")
    d.add("tv_share_g", "Terminal value share of EV", "%", const="={$pv_tv_g}/{$ev_g}", fmt="pct")
    d.add("price_g", "Implied share price", "$", const="=({$ev_g}-{$net_debt})/{WACC.$shares_out}*{$roll}", fmt="ps", style="total")
    d.add("upside_g", "Upside / (downside) vs market", "%", const="={$price_g}/{WACC.$price}-1", fmt="pct")
    d.add("implied_mult", "Implied exit EV/EBITDA", "x", const=f"={{$tv_g}}/{EB}", fmt="x")
    d.blank()
    d.section("Exit-multiple method")
    d.add("exit_mult", "Exit EV/EBITDA (comps median)", "x", const="=" + comps_cells["median_ev_ebitda"], fmt="x")
    d.add("tv_x", "Terminal value", "$m", const=f"={EB}*{{$exit_mult}}")
    d.add("pv_tv_x", "PV of terminal value (end of final year)", "$m", const=f"={{$tv_x}}/(1+{{WACC.$wacc}})^{FN}")
    d.add("ev_x", "Enterprise value", "$m", const="={$sum_pv}+{$pv_tv_x}", style="total")
    d.add("tv_share_x", "Terminal value share of EV", "%", const="={$pv_tv_x}/{$ev_x}", fmt="pct")
    d.add("price_x", "Implied share price", "$", const="=({$ev_x}-{$net_debt})/{WACC.$shares_out}*{$roll}", fmt="ps", style="total")
    d.add("upside_x", "Upside / (downside) vs market", "%", const="={$price_x}/{WACC.$price}-1", fmt="pct")
    d.add("implied_g", "Implied perpetual growth", "%", const=f"=({{$tv_x}}*{{WACC.$wacc}}-{U})/({{$tv_x}}+{U})", fmt="pct")
    d.blank()
    d.section("Reverse DCF: what the market price implies")
    d.add("market_ev", "Market enterprise value (price deflated to FYE)", "$m",
          const="={WACC.$price}/{$roll}*{WACC.$shares_out}+{$net_debt}")
    d.add("tv_needed", "Terminal value needed", "$m", const=f"=({{$market_ev}}-{{$sum_pv}})/{DFN}")
    d.add("implied_g_mkt", "Perpetual growth implied by the market price", "%",
          const=f"=({{$tv_needed}}*{{WACC.$wacc}}-{U})/({{$tv_needed}}+{U})", fmt="pct", style="total")

    # ---------------------------------------------------------------- Sensitivity
    s = m.sheet("Sensitivity", "Implied share price sensitivities ($/share)", timeline=False)
    s.col_widths = {"A": 4, "B": 24, **{chr(ord("C") + k): 12 for k in range(GRID_STEPS)}}
    dc = m.sheets["DCF"]
    ufcf_rng = f"'DCF'!${tl.col(inp.n_hist)}${dc.row('ufcf')}:${tl.col(lf)}${dc.row('ufcf')}"
    per_rng = f"'DCF'!${tl.col(inp.n_hist)}${dc.row('period')}:${tl.col(lf)}${dc.row('period')}"
    u_n = f"'DCF'!${tl.col(lf)}${dc.row('ufcf')}"
    per_n = f"'DCF'!${tl.col(lf)}${dc.row('period')}"
    fn = f"'DCF'!${tl.col(lf)}$7"
    ebitda_n = f"'IS'!${tl.col(lf)}${m.sheets['IS'].row('ebitda')}"
    nd, roll, sh = f"'DCF'!$C${dc.row('net_debt')}", f"'DCF'!$C${dc.row('roll')}", f"'WACC'!$C${w.row('shares_out')}"
    wacc, g, step_w = f"'WACC'!$C${w.row('wacc')}", f"'WACC'!$C${w.row('terminal_growth')}", f"'WACC'!$C${w.row('wacc_step')}"
    cols = [chr(ord("C") + k) for k in range(GRID_STEPS)]
    mid = GRID_STEPS // 2

    def grid(top: int, title: str, row_label: str, center_row: str, step_row: str, row_fmt: str, cell_tmpl: str) -> None:
        s.cell(f"B{top}", title, bold=True, size=12)
        s.cell(f"B{top + 1}", f"{row_label} (down) / WACC (across)", italic=True, color="808080")
        hdr = top + 2
        s.cell(f"{cols[mid]}{hdr}", f"={wacc}", fmt="pct", bold=True)
        for k in range(mid - 1, -1, -1):
            s.cell(f"{cols[k]}{hdr}", f"={cols[k + 1]}{hdr}-{step_w}", fmt="pct", bold=True)
        for k in range(mid + 1, GRID_STEPS):
            s.cell(f"{cols[k]}{hdr}", f"={cols[k - 1]}{hdr}+{step_w}", fmt="pct", bold=True)
        rows = [hdr + 1 + k for k in range(GRID_STEPS)]
        s.cell(f"B{rows[mid]}", f"={center_row}", fmt=row_fmt, bold=True)
        for k in range(mid - 1, -1, -1):
            s.cell(f"B{rows[k]}", f"=B{rows[k + 1]}-{step_row}", fmt=row_fmt, bold=True)
        for k in range(mid + 1, GRID_STEPS):
            s.cell(f"B{rows[k]}", f"=B{rows[k - 1]}+{step_row}", fmt=row_fmt, bold=True)
        for r in rows:
            for col in cols:
                s.cell(f"{col}{r}", cell_tmpl.format(w=f"{col}${hdr}", x=f"$B{r}"), fmt="ps",
                       **({"fill": "FFF2CC"} if (r == rows[mid] and col == cols[mid]) else {}))

    pv_part = f"SUMPRODUCT({ufcf_rng},1/(1+{{w}})^{per_rng})"
    grid(4, "Perpetuity-growth method", "Terminal growth", g, f"'WACC'!$C${w.row('growth_step')}", "pct",
         f"=({pv_part}+{u_n}*(1+{{x}})/({{w}}-{{x}})/(1+{{w}})^{per_n}-{nd})/{sh}*{roll}")
    grid(14, "Exit-multiple method", "Exit EV/EBITDA", f"'DCF'!$C${dc.row('exit_mult')}", f"'WACC'!$C${w.row('multiple_step')}",
         "x", f"=({pv_part}+{ebitda_n}*{{x}}/(1+{{w}})^{fn}-{nd})/{sh}*{roll}")
    inner = {"gordon": f"'Sensitivity'!$D$8:$F$10", "exit": f"'Sensitivity'!$D$18:$F$20"}

    # ---------------------------------------------------------------- Football field
    f = m.sheet("Football", "Valuation summary: football field ($/share)", timeline=False)
    f.col_widths = {"A": 56, "B": 12, "C": 12, "D": 12}
    for col, h in zip("ABCD", ["Method", "Low", "High", "Range"]):
        f.cell(f"{col}4", h, bold=True)
    sh_abs = f"'WACC'!$C${w.row('shares_out')}"
    rows = [
        ("DCF, perpetuity growth (WACC +/-1 step, g +/-1 step)", f"=MIN({inner['gordon']})", f"=MAX({inner['gordon']})"),
        ("DCF, exit multiple (WACC +/-1 step, multiple +/-1 step)", f"=MIN({inner['exit']})", f"=MAX({inner['exit']})"),
        ("Trading comps, EV/EBITDA (25th-75th percentile)",
         f"=({comps_cells['q1_ev_ebitda']}*{comps_cells['ebitda0']}-{nd})/{sh_abs}",
         f"=({comps_cells['q3_ev_ebitda']}*{comps_cells['ebitda0']}-{nd})/{sh_abs}"),
        ("Trading comps, P/E (25th-75th percentile)", f"={comps_cells['q1_pe']}*{comps_cells['eps0']}",
         f"={comps_cells['q3_pe']}*{comps_cells['eps0']}"),
        ("52-week trading range", v.lo_52w, v.hi_52w),
    ]
    for k, (label, lo, hi) in enumerate(rows):
        r = 5 + k
        f.cell(f"A{r}", label)
        for col, x in (("B", lo), ("C", hi)):
            if isinstance(x, (int, float)):
                f.cell(f"{col}{r}", x, input=True, fmt="ps", note=v.notes["52w"])
            else:
                f.cell(f"{col}{r}", x, fmt="ps")
        f.cell(f"D{r}", f"=C{r}-B{r}", fmt="ps")
    f.cell("A11", "Current share price", bold=True)
    f.cell("B11", f"='WACC'!$C${w.row('price')}", fmt="ps", bold=True)
    m.charts = getattr(m, "charts", []) + [("Football", _football_chart)]


def _football_chart(ws) -> None:
    ch = BarChart()
    ch.type, ch.grouping, ch.overlap = "bar", "stacked", 100
    ch.title, ch.y_axis.title = "Implied value per share ($)", None
    ch.add_data(Reference(ws, min_col=2, min_row=4, max_row=9), titles_from_data=True)
    ch.add_data(Reference(ws, min_col=4, min_row=4, max_row=9), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=9))
    ch.series[0].graphicalProperties = GraphicalProperties(noFill=True)
    ch.series[0].graphicalProperties.line.noFill = True
    ch.series[1].graphicalProperties.solidFill = "1F3864"
    ch.legend = None
    ch.height, ch.width = 8, 18
    ws.add_chart(ch, "A13")
