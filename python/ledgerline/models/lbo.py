"""Workbook 03: LBO of Skechers by 3G Capital (docs/models/lbo.md). Reference: ref/lbo.py."""
from __future__ import annotations

from ..build.grid import Model, Timeline
from .assumptions import CASES
from .lbo_inputs import LBOInputs
from .three_statement import CASE_LABEL

HIST = [("revenue", "Revenue"), ("operating_income", "Operating income (EBIT)"), ("da", "Depreciation and amortisation"),
        ("capex", "Capital expenditure (cash sign)"), ("interest_expense", "Interest expense"), ("net_income", "Net income to parent"),
        ("nci_income", "NCI share of net income"), ("cash", "Cash and equivalents"), ("st_investments", "Short-term investments"),
        ("receivables", "Receivables"), ("inventory", "Inventory"), ("other_current_assets", "Other current assets"),
        ("accounts_payable", "Accounts payable"), ("accrued_liabilities", "Accrued liabilities"),
        ("employee_liabilities", "Accrued salaries and benefits"), ("deferred_revenue", "Deferred revenue"),
        ("other_current_liabilities", "Other current liabilities (plug)"), ("short_term_debt", "Short-term borrowings"),
        ("current_debt", "Current portion of long-term debt"), ("lt_debt", "Long-term debt"),
        ("nci_equity", "Non-controlling interests (equity)"), ("temp_equity", "Redeemable NCI (temporary equity)")]
DRIVER_LABEL = {"revenue_growth": "Revenue growth", "ebitda_margin": "EBITDA margin", "da_pct": "D&A % revenue",
                "capex_pct": "Capex % revenue", "nwc_pct": "Trade working capital % revenue"}
TX_LABEL = {
    "price_per_share": ("Offer price per share", "$", "ps"), "shares_common": ("Common shares outstanding", "m", "m1"),
    "shares_awards": ("RSAs and RSUs cashed out", "m", "m1"), "cash_consideration": ("Cash consideration (equity)", "$m", "m1"),
    "rollover_equity": ("Rollover equity (Mixed Election units)", "$m", "m1"), "debt_repaid": ("Existing debt repaid", "$m", "m1"),
    "financing_fees": ("Financing fees and OID", "$m", "m1"), "rcf_fees": ("Revolver fees", "$m", "m1"),
    "transaction_costs": ("Transaction costs", "$m", "m1"), "tl_usd": ("Term loan B, USD tranche", "$m", "m1"),
    "tl_total": ("Term loans, total (USD equivalent)", "$m", "m1"), "ssn": ("Senior secured notes (EUR, USD equivalent)", "$m", "m1"),
    "pik_notes": ("Senior PIK toggle notes", "$m", "m1"), "sponsor_equity": ("Sponsor equity (3G Fund VI)", "$m", "m1"),
    "spread_usd": ("USD term loan margin over SOFR", "%", "pct"), "spread_eur": ("EUR term loan margin over Euribor", "%", "pct"),
    "ssn_rate": ("Senior secured notes coupon", "%", "pct"), "pik_cash_rate": ("PIK notes cash-pay rate", "%", "pct"),
    "pik_pik_rate": ("PIK notes PIK rate", "%", "pct"), "rcf_capacity": ("Revolver capacity", "$m", "m"),
}
J_LABEL = {
    "rcf_spread": ("Revolver margin over SOFR", "%", "pct"), "commitment_fee": ("Revolver commitment fee (undrawn)", "%", "pct"),
    "tl_amort": ("Term loan amortisation (% of original)", "%", "pct"), "sweep_pct": ("Excess cash flow sweep", "%", "pct"),
    "min_cash": ("Minimum cash", "$m", "m"), "existing_debt_rate": ("Rate on remaining existing debt", "%", "pct"),
    "tax_rate": ("Cash tax rate", "%", "pct"), "nci_pct": ("NCI distributions (% of net income)", "%", "pct"),
    "covenant_max_1l": ("Springing first-lien net leverage covenant", "x", "x"), "exit_year": ("Exit year (years after close)", "years", "n"),
    "mip_pct": ("Management incentive pool (% of exit equity)", "%", "pct"),
}


def timeline(inp: LBOInputs) -> Timeline:
    return Timeline(inp.period_ends(), inp.labels(), inp.n_hist)


def add_lbo(m: Model, inp: LBOInputs) -> None:
    tl = m.timeline
    n_h, lh, lf = inp.n_hist, inp.n_hist - 1, tl.n - 1

    s = m.sheet("Inputs", "Inputs: transaction terms (sourced), judgement, switches")
    s.section("Switches")
    s.add("scenario", "Live scenario (1 Base, 2 Upside, 3 Downside)", "count", const=inp.scenario, fmt="n")
    s.add("scenario_name", "Live scenario name", "", const='=CHOOSE({$scenario},"Base","Upside","Downside")', fmt="text")
    s.blank()
    s.section("Transaction terms (DEFM14C information statement)")
    for k, (label, unit, fmt) in TX_LABEL.items():
        s.add(k, label, unit, const=inp.tx[k], fmt=fmt, const_note=inp.src[k])
    s.blank()
    s.section("Judgement")
    for k, (label, unit, fmt) in J_LABEL.items():
        s.add(k, label, unit, const=inp.j[k], fmt=fmt, const_note=inp.src[k])
    s.add("price_step", "Sensitivity step: offer price", "$", const=3.0, fmt="ps", const_note="Judgement: grid step.")
    s.add("mult_step", "Sensitivity step: exit multiple", "x", const=1.0, fmt="x", const_note="Judgement: grid step.")
    s.blank()
    s.section("Market rates by year (judgement)")
    for k, label, fmt in (("sofr", "3-month Term SOFR", "pct"), ("euribor", "3-month Euribor", "pct"),
                          ("pik_toggle", "PIK election (1 = PIK, 0 = cash pay)", "flag")):
        r = s.add(k, label, "%" if fmt == "pct" else "flag", fcst=[None] * n_h + inp.rates[k], style="input", fmt=fmt)
        r.note = inp.src[k]

    h = m.sheet("Hist", f"Historical financials: {inp.history.entity} (10-K XBRL)")
    idx = list(inp.hist_slice)
    for key, label in HIST:
        r = h.add(key, label, "$m", hist=inp.h(key) + [None] * inp.n_fcst, style="input")
        r.note = "Source per year: " + "; ".join(f"{inp.labels()[j]}: {inp.history.source[key][i]}" for j, i in enumerate(idx))

    sc = m.sheet("Scenarios", "Operating scenarios (judgement, rationale in notes)")
    for d, cases in inp.drivers.items():
        sc.section(DRIVER_LABEL[d])
        for case in CASES:
            r = sc.add(f"{d}_{case}", f"  {CASE_LABEL[case]}", "%", fcst=[None] * n_h + cases[case], style="input", fmt="pct")
            if case == "base":
                r.note = inp.src[d]

    dv = m.sheet("Drivers", "Live operating drivers")
    hist_tmpl = {
        "revenue_growth": lambda i: "={Hist.revenue}/{Hist.revenue@-1}-1" if i >= 1 else None,
        "ebitda_margin": "=({Hist.operating_income}+{Hist.da})/{Hist.revenue}",
        "da_pct": "={Hist.da}/{Hist.revenue}",
        "capex_pct": "=-{Hist.capex}/{Hist.revenue}",
        "nwc_pct": "={Operating.nwc}/{Hist.revenue}",
    }
    for d in inp.drivers:
        dv.add(d, DRIVER_LABEL[d], "%", hist=hist_tmpl[d], fmt="pct",
               fcst="=CHOOSE({Inputs.$scenario}," + ",".join("{Scenarios.%s_%s}" % (d, c) for c in CASES) + ")")

    # ---------------------------------------------------------------- Transaction
    t = m.sheet("Transaction", "Sources and uses, entry valuation", timeline=True)
    t.section("Uses")
    t.add("u_cash", "Cash consideration to shareholders and award holders", "$m", const="={Inputs.$cash_consideration}")
    t.add("u_roll", "Rollover equity", "$m", const="={Inputs.$rollover_equity}")
    t.add("u_debt", "Repay existing debt", "$m", const="={Inputs.$debt_repaid}")
    t.add("u_fees", "Financing fees, OID and revolver fees", "$m", const="={Inputs.$financing_fees}+{Inputs.$rcf_fees}")
    t.add("u_costs", "Transaction costs", "$m", const="={Inputs.$transaction_costs}")
    t.add("uses", "Total uses", "$m", const="=SUM({$u_cash}:{$u_costs})", style="total")
    t.blank()
    t.section("Sources")
    t.add("s_tlu", "Term loan B, USD", "$m", const="={Inputs.$tl_usd}")
    t.add("s_tle", "Term loan B, EUR (USD equivalent)", "$m", const="={Inputs.$tl_total}-{Inputs.$tl_usd}")
    t.add("s_ssn", "Senior secured notes", "$m", const="={Inputs.$ssn}")
    t.add("s_pik", "Senior PIK toggle notes", "$m", const="={Inputs.$pik_notes}")
    t.add("s_sponsor", "Sponsor equity", "$m", const="={Inputs.$sponsor_equity}")
    t.add("s_roll", "Rollover equity", "$m", const="={Inputs.$rollover_equity}")
    t.add("s_cash", "Cash from Skechers' balance sheet (plug)", "$m", const="={$uses}-SUM({$s_tlu}:{$s_roll})")
    t.add("sources", "Total sources", "$m", const="=SUM({$s_tlu}:{$s_cash})", style="total")
    t.blank()
    t.section("Entry valuation (FY2024 EBITDA)")
    t.add("ebitda0", "FY2024 EBITDA (EBIT + D&A)", "$m", const="={Hist.operating_income#%d}+{Hist.da#%d}" % (lh, lh))
    t.add("debt_pre", "Pre-deal debt", "$m", const="={Hist.short_term_debt#%d}+{Hist.current_debt#%d}+{Hist.lt_debt#%d}" % (lh, lh, lh))
    t.add("existing_debt", "Existing debt remaining after close", "$m", const="={$debt_pre}-{Inputs.$debt_repaid}")
    t.add("nci0", "NCI claim (book NCI + redeemable NCI)", "$m", const="={Hist.nci_equity#%d}+{Hist.temp_equity#%d}" % (lh, lh))
    t.add("cash0", "Cash at close", "$m", const="={Hist.cash#%d}-{$s_cash}" % lh)
    t.add("headline_ev", "Headline EV (offer equity + net debt + NCI)", "$m",
          const="={$u_cash}+{$u_roll}+{$debt_pre}-{Hist.cash#%d}-{Hist.st_investments#%d}+{$nci0}" % (lh, lh))
    t.add("headline_mult", "Headline EV / FY2024 EBITDA", "x", const="={$headline_ev}/{$ebitda0}", fmt="x")
    t.add("E0", "Equity invested (sponsor + rollover)", "$m", const="={$s_sponsor}+{$s_roll}", style="total")
    t.add("claims0", "Net debt + NCI at close", "$m",
          const="={$s_tlu}+{$s_tle}+{$s_ssn}+{$s_pik}+{$existing_debt}-{$cash0}+{$nci0}")
    t.add("entry_ev", "Entry EV incl. fees (equity + net claims)", "$m", const="={$E0}+{$claims0}")
    t.add("entry_mult", "Entry EV / FY2024 EBITDA (incl. fees)", "x", const="={$entry_ev}/{$ebitda0}", fmt="x", style="total")
    t.add("leverage_close", "Total debt at close / EBITDA", "x",
          const="=({$s_tlu}+{$s_tle}+{$s_ssn}+{$s_pik}+{$existing_debt})/{$ebitda0}", fmt="x")
    t.add("sponsor_share", "Sponsor share of equity", "%", const="={$s_sponsor}/{$E0}", fmt="pct")

    # ---------------------------------------------------------------- Operating
    o = m.sheet("Operating", "Operating model and levered free cash flow")
    o.add("revenue", "Revenue", "$m", hist="={Hist.revenue}", fcst="={revenue@-1}*(1+{Drivers.revenue_growth})", style="total")
    o.add("ebitda", "EBITDA", "$m", hist="={Hist.operating_income}+{Hist.da}", fcst="={revenue}*{Drivers.ebitda_margin}")
    o.add("da", "D&A", "$m", hist="={Hist.da}", fcst="={revenue}*{Drivers.da_pct}")
    o.add("ebit", "EBIT", "$m", all="={ebitda}-{da}", style="total")
    o.add("capex", "Capex", "$m", hist="=-{Hist.capex}", fcst="={revenue}*{Drivers.capex_pct}")
    o.add("nwc", "Trade working capital", "$m",
          hist="={Hist.receivables}+{Hist.inventory}+{Hist.other_current_assets}-{Hist.accounts_payable}-({Hist.accrued_liabilities}"
               "+{Hist.employee_liabilities}+{Hist.deferred_revenue}+{Hist.other_current_liabilities})",
          fcst="={revenue}*{Drivers.nwc_pct}")
    o.add("change_nwc", "Working-capital cash impact", "$m", fcst="={nwc@-1}-{nwc}")
    o.add("interest_total", "Interest expense (cash + PIK + fees)", "$m", fcst="={Debt.interest_total}")
    o.add("taxes", "Cash taxes", "$m", fcst="=MAX(0,{ebit}-{interest_total})*{Inputs.$tax_rate}")
    o.add("ni_total", "Net income incl. NCI", "$m", fcst="={ebit}-{interest_total}-{taxes}", style="total")
    o.add("nci_dist", "Distributions to NCI partners", "$m", fcst="={Inputs.$nci_pct}*MAX(0,{ni_total})")
    o.add("cash_interest", "Cash interest", "$m", fcst="={Debt.cash_interest}")
    o.add("lfcf", "Levered free cash flow (before debt repayment)", "$m",
          fcst="={ebitda}-{capex}+{change_nwc}-{taxes}-{cash_interest}-{nci_dist}", style="total")

    # ---------------------------------------------------------------- Debt
    d = m.sheet("Debt", "Debt schedule: tranches, revolver, sweep, covenants")
    d.section("Cash waterfall")
    d.section("The last history column shows pro forma balances at close (deal modelled at FY2024 year end)")
    d.add("cash_open", "Opening cash", "$m", fcst="={cash@-1}")
    d.add("lfcf", "Levered free cash flow", "$m", fcst="={Operating.lfcf}")
    d.add("amort", "Mandatory amortisation", "$m", fcst="={tlu_amort}+{tle_amort}")
    d.add("cash_pre", "Cash before revolver and sweep", "$m", fcst="={cash_open}+{lfcf}-{amort}")
    d.add("rcf_draw", "Revolver draw / (repayment)", "$m",
          fcst="=MIN(MAX({Inputs.$min_cash}-{cash_pre},-{rcf_open}),{Inputs.$rcf_capacity}-{rcf_open})")
    d.add("excess", "Excess cash above minimum", "$m", fcst="=MAX(0,{cash_pre}+{rcf_draw}-{Inputs.$min_cash})")
    d.add("tl_after_amort", "Term loans after amortisation", "$m", fcst="={tlu_open}-{tlu_amort}+{tle_open}-{tle_amort}")
    d.add("sweep", "Cash sweep to term loans", "$m", fcst="=MIN({excess}*{Inputs.$sweep_pct},{tl_after_amort})")
    d.add("cash", "Closing cash", "$m", hist=lambda i: "={Transaction.$cash0}" if i == lh else None, fcst="={cash_pre}+{rcf_draw}-{sweep}", style="total")
    d.blank()

    def tranche(key, label, open0, amort=None, sweep=None, accrue=None):
        d.section(label)
        d.add(f"{key}_open", "Opening balance", "$m", fcst="={%s@-1}" % key)
        rows = []
        if amort:
            d.add(f"{key}_amort", "Mandatory amortisation", "$m", fcst=amort); rows.append(f"-{{{key}_amort}}")
        if sweep:
            d.add(f"{key}_sweep", "Sweep", "$m", fcst=sweep); rows.append(f"-{{{key}_sweep}}")
        if accrue:
            d.add(f"{key}_accrued", "PIK interest accrued", "$m", fcst=accrue); rows.append(f"+{{{key}_accrued}}")
        d.add(key, "Closing balance", "$m", hist=lambda i: open0 if i == lh else None,
              fcst=f"={{{key}_open}}" + "".join(rows), style="total")

    tranche("tlu", "Term loan B, USD", "={Transaction.$s_tlu}",
            amort="=MIN({Inputs.$tl_amort}*{Transaction.$s_tlu},{tlu_open})",
            sweep="=IF({tl_after_amort}>0,{sweep}*({tlu_open}-{tlu_amort})/{tl_after_amort},0)")
    tranche("tle", "Term loan B, EUR", "={Transaction.$s_tle}",
            amort="=MIN({Inputs.$tl_amort}*{Transaction.$s_tle},{tle_open})", sweep="={sweep}-{tlu_sweep}")
    tranche("ssn", "Senior secured notes (bullet 2032)", "={Transaction.$s_ssn}")
    tranche("pik", "Senior PIK toggle notes (bullet 2033)", "={Transaction.$s_pik}", accrue="={int_pik}*{Inputs.pik_toggle}")
    d.section("Revolver")
    d.add("rcf_open", "Opening balance", "$m", fcst="={rcf@-1}")
    d.add("rcf", "Closing balance", "$m", hist=lambda i: 0 if i == lh else None, fcst="={rcf_open}+{rcf_draw}", style="total")
    d.section("Existing debt (remaining)")
    d.add("existing", "Balance (held flat)", "$m", fcst="={Transaction.$existing_debt}")
    d.blank()
    d.section("Interest (on opening balances)")
    d.add("int_tlu", "Term loan USD", "$m", fcst="=({Inputs.sofr}+{Inputs.$spread_usd})*{tlu_open}")
    d.add("int_tle", "Term loan EUR", "$m", fcst="=({Inputs.euribor}+{Inputs.$spread_eur})*{tle_open}")
    d.add("int_ssn", "Senior secured notes", "$m", fcst="={Inputs.$ssn_rate}*{ssn_open}")
    d.add("int_pik", "PIK toggle notes", "$m",
          fcst="=IF({Inputs.pik_toggle}=1,{Inputs.$pik_pik_rate},{Inputs.$pik_cash_rate})*{pik_open}")
    d.add("int_rcf", "Revolver (drawn + commitment fee)", "$m",
          fcst="=({Inputs.sofr}+{Inputs.$rcf_spread})*{rcf_open}+{Inputs.$commitment_fee}*({Inputs.$rcf_capacity}-{rcf_open})")
    d.add("int_existing", "Existing debt", "$m", fcst="={Inputs.$existing_debt_rate}*{existing}")
    d.add("interest_total", "Total interest", "$m", fcst="=SUM({int_tlu}:{int_existing})", style="total")
    d.add("cash_interest", "Cash interest", "$m", fcst="={interest_total}-{pik_accrued}")
    d.blank()
    d.section("Credit statistics")
    d.add("total_debt", "Total debt", "$m", fcst="={tlu}+{tle}+{ssn}+{pik}+{rcf}+{existing}", style="total")
    d.add("net_debt", "Net debt", "$m", fcst="={total_debt}-{cash}")
    d.add("lev_1l", "First-lien net leverage", "x", fcst="=({tlu}+{tle}+{ssn}+{rcf}-{cash})/{Operating.ebitda}", fmt="x")
    d.add("lev_total", "Total net leverage", "x", fcst="={net_debt}/{Operating.ebitda}", fmt="x")
    d.add("icr", "EBITDA / cash interest", "x", fcst="={Operating.ebitda}/{cash_interest}", fmt="x")
    d.add("headroom", "Covenant headroom (turns of EBITDA)", "x", fcst="={Inputs.$covenant_max_1l}-{lev_1l}", fmt="x")
    d.add("breach", "Covenant breach flag (informational)", "flag", fcst="=IF({headroom}<0,1,0)", fmt="flag")

    # ---------------------------------------------------------------- Returns
    r = m.sheet("Returns", "Returns to equity")
    r.add("exit_mult", "Exit EV / EBITDA (= entry multiple)", "x", const="={Transaction.$entry_mult}", fmt="x")
    r.add("nci_claim", "NCI claim (grows with EBITDA)", "$m", fcst="={Transaction.$nci0}*{Operating.ebitda}/{Transaction.$ebitda0}")
    r.add("exit_ev", "Exit enterprise value", "$m", fcst="={Operating.ebitda}*{$exit_mult}")
    r.add("exit_equity", "Exit equity value", "$m", fcst="={exit_ev}-{Debt.net_debt}-{nci_claim}")
    r.add("investor_equity", "Equity to investors after MIP", "$m", fcst="={exit_equity}*(1-{Inputs.$mip_pct})", style="total")
    r.add("flows", "Investor cash flows (entry, exit)", "$m",
          hist=lambda i: "=-{Transaction.$E0}" if i == lh else None,
          fcst="=IF({fcst_n}={Inputs.$exit_year},{investor_equity},0)")
    r.blank()
    F = "{flows#%d}:{flows#%d}" % (lh, lf)
    r.add("x_equity", "Investor equity at exit", "$m", const="=INDEX({investor_equity:fcst},{Inputs.$exit_year})")
    r.add("moic", "MOIC", "x", const="={$x_equity}/{Transaction.$E0}", fmt="x", style="total")
    r.add("irr", "IRR (IRR function on cash flows)", "%", const="=IRR(%s)" % F, fmt="pct", style="total")
    r.add("irr_closed", "IRR (closed form, single exit)", "%", const="={$moic}^(1/{Inputs.$exit_year})-1", fmt="pct")
    r.add("sponsor_proceeds", "Sponsor proceeds at exit", "$m", const="={$x_equity}*{Transaction.$sponsor_share}")
    r.blank()
    r.section("Value creation (exit year)")
    X = lambda row: "INDEX({%s:fcst},{Inputs.$exit_year})" % row
    r.add("x_ebitda", "Exit-year EBITDA", "$m", const="=" + X("Operating.ebitda"))
    r.add("x_claims", "Exit-year net debt + NCI", "$m", const="=" + X("Debt.net_debt") + "+" + X("nci_claim"))
    r.add("attr_ebitda", "EBITDA growth", "$m", const="=({$x_ebitda}-{Transaction.$ebitda0})*{Transaction.$entry_mult}")
    r.add("attr_multiple", "Multiple expansion", "$m", const="=({$exit_mult}-{Transaction.$entry_mult})*{$x_ebitda}")
    r.add("attr_delever", "Deleveraging (fall in net claims)", "$m", const="={Transaction.$claims0}-{$x_claims}")
    r.add("attr_mip", "Management incentive pool", "$m", const="=-{Inputs.$mip_pct}*" + X("exit_equity"))
    r.add("value_created", "Value created for investors", "$m", const="={$x_equity}-{Transaction.$E0}", style="total")

    # ---------------------------------------------------------------- Sensitivity
    g = m.sheet("Sensitivity", "IRR sensitivities", timeline=False)
    g.col_widths = {"A": 4, "B": 22, **{chr(ord("C") + k): 11 for k in range(5)}}
    cols = "CDEFG"
    ref = lambda sh, key: f"'{sh}'!$C${m.sheets[sh].row(key)}"
    E0, mip, xy = ref("Transaction", "E0"), ref("Inputs", "mip_pct"), ref("Inputs", "exit_year")
    px, shares = ref("Inputs", "price_per_share"), f"({ref('Inputs', 'shares_common')}+{ref('Inputs', 'shares_awards')})"
    xe, xc = ref("Returns", "x_ebitda"), ref("Returns", "x_claims")
    g.cell("B3", "IRR: offer price (down) x exit multiple (across)", bold=True, size=12)
    g.cell("E5", f"={ref('Transaction', 'entry_mult')}", fmt="x", bold=True)
    g.cell("D5", f"=E5-{ref('Inputs', 'mult_step')}", fmt="x", bold=True); g.cell("C5", f"=D5-{ref('Inputs', 'mult_step')}", fmt="x", bold=True)
    g.cell("F5", f"=E5+{ref('Inputs', 'mult_step')}", fmt="x", bold=True); g.cell("G5", f"=F5+{ref('Inputs', 'mult_step')}", fmt="x", bold=True)
    g.cell("B8", f"={px}", fmt="ps", bold=True)
    g.cell("B7", f"=B8-{ref('Inputs', 'price_step')}", fmt="ps", bold=True); g.cell("B6", f"=B7-{ref('Inputs', 'price_step')}", fmt="ps", bold=True)
    g.cell("B9", f"=B8+{ref('Inputs', 'price_step')}", fmt="ps", bold=True); g.cell("B10", f"=B9+{ref('Inputs', 'price_step')}", fmt="ps", bold=True)
    for rr in range(6, 11):
        for c in cols:
            g.cell(f"{c}{rr}", f"=(({xe}*{c}$5-{xc})*(1-{mip})/({E0}+($B{rr}-{px})*{shares}))^(1/{xy})-1", fmt="pct")
    g.cell("B13", "IRR: exit year (down) x exit multiple (across)", bold=True, size=12)
    for c in cols:
        g.cell(f"{c}15", f"={c}5", fmt="x", bold=True)
    deb, nci, eb = m.sheets["Debt"], m.sheets["Returns"], m.sheets["Operating"]
    rng = lambda sh, key: f"'{sh.name}'!${tl.col(n_h)}${sh.row(key)}:${tl.col(lf)}${sh.row(key)}"
    for k, yy in enumerate([3, 4, 5, 6, 7]):
        rr = 16 + k
        g.cell(f"B{rr}", yy, input=True, fmt="n", note="Exit year (years after close).")
        for c in cols:
            g.cell(f"{c}{rr}", f"=((INDEX({rng(eb, 'ebitda')},$B{rr})*{c}$15-INDEX({rng(deb, 'net_debt')},$B{rr})"
                               f"-INDEX({rng(nci, 'nci_claim')},$B{rr}))*(1-{mip})/{E0})^(1/$B{rr})-1", fmt="pct")

    # ---------------------------------------------------------------- Checks
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)")
    checks = [
        ("su_balance", "Sources = uses", dict(const="={Transaction.$sources}-{Transaction.$uses}")),
        ("attr_ties", "Value-creation bridge sums to value created",
         dict(const="={Returns.$attr_ebitda}+{Returns.$attr_multiple}+{Returns.$attr_delever}+{Returns.$attr_mip}-{Returns.$value_created}")),
        ("irr_agree", "IRR function = closed form", dict(const="=ROUND({Returns.$irr}-{Returns.$irr_closed},{$irr_dp})")),
        ("debt_nonneg", "No tranche negative", dict(fcst="=MIN(0,{Debt.tlu})+MIN(0,{Debt.tle})+MIN(0,{Debt.rcf})")),
        ("rcf_cap", "Revolver within capacity", dict(fcst="=MAX(0,{Debt.rcf}-{Inputs.$rcf_capacity})")),
        ("cash_nonneg", "Cash not negative", dict(fcst="=MIN(0,{Debt.cash})")),
        ("cash_roll", "Cash roll-forward", dict(fcst="={Debt.cash}-{Debt.cash_open}-{Operating.lfcf}+{Debt.amort}-{Debt.rcf_draw}+{Debt.sweep}")),
    ]
    for key, label, kw in checks:
        if "const" in kw:
            ck.add(key, label, "", style="check", **kw)
        else:
            ck.add(key, label, "$m", const="=SUMPRODUCT(ABS({%s:all}))" % key, style="check", **kw)
    ck.blank()
    ck.add("irr_dp", "IRR comparison precision (decimal places)", "count", const=6, fmt="n",
           const_note="IRR() iterates to about 1e-8; agreement is required to 6 decimal places (ADR 0005: IRR to 1e-6).")
    ck.add("tolerance", "Tolerance", "$m", const=0.001, fmt="0.000")
    ck.add("master", "MASTER CHECK (0 = all pass)", "count",
           const="=IF(SUMPRODUCT(ABS({$su_balance}:{$cash_roll}))<{$tolerance},0,1)", style="total", fmt="flag")
    m.names["MasterCheck"] = f"'Checks'!$C${ck.row('master')}"
