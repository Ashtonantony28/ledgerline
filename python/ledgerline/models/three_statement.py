"""Workbook 01: three-statement operating model (sheets added to a grid.Model).

The formulas here implement docs/models/three-statement.md. The Python reference in
ref/three_statement.py implements the same document independently; CI compares the two.
"""
from __future__ import annotations

from ..build.grid import Model, Timeline
from .assumptions import CASES, Inputs

CASE_LABEL = {"base": "Base", "upside": "Upside", "downside": "Downside"}

HIST_ITEMS = [  # (key, label, fmt) shown on the Hist sheet, model units
    ("revenue", "Revenue", "m"), ("cogs", "Cost of goods sold", "m"), ("sga", "SG&A", "m"),
    ("other_opex", "Other operating expense (plug)", "m"), ("operating_income", "Operating income", "m"),
    ("interest_expense", "Interest expense", "m"), ("other_nonop_income", "Interest and other income (plug)", "m"),
    ("pretax_income", "Pre-tax income", "m"), ("income_tax", "Income tax", "m"),
    ("other_below_tax", "Other below tax (plug)", "m"), ("net_income_total", "Net income incl. NCI", "m"),
    ("nci_income", "NCI share of net income", "m"), ("net_income", "Net income to parent", "m"),
    ("shares_diluted", "Diluted weighted shares", "m1"), ("eps_diluted", "Diluted EPS (reported)", "ps"),
    ("da", "Depreciation and amortisation", "m"), ("sbc", "Stock-based compensation", "m"),
    ("cash", "Cash and equivalents", "m"), ("st_investments", "Short-term investments", "m"),
    ("receivables", "Receivables", "m"), ("inventory", "Inventory", "m"),
    ("other_current_assets", "Other current assets (plug)", "m"), ("total_current_assets", "Total current assets", "m"),
    ("ppe_net", "PP&E, net", "m"), ("op_lease_rou", "Operating lease ROU assets", "m"), ("goodwill", "Goodwill", "m"),
    ("intangibles", "Intangibles", "m"), ("other_nc_assets", "Other non-current assets (plug)", "m"),
    ("total_assets", "Total assets", "m"), ("accounts_payable", "Accounts payable", "m"),
    ("accrued_liabilities", "Accrued liabilities", "m"), ("employee_liabilities", "Accrued salaries and benefits", "m"),
    ("deferred_revenue", "Deferred revenue", "m"), ("short_term_debt", "Short-term borrowings", "m"),
    ("current_debt", "Current portion of long-term debt", "m"), ("op_lease_liab_current", "Operating lease liabilities, current", "m"),
    ("other_current_liabilities", "Other current liabilities (plug)", "m"),
    ("total_current_liabilities", "Total current liabilities", "m"), ("lt_debt", "Long-term debt", "m"),
    ("op_lease_liab_noncurrent", "Operating lease liabilities, non-current", "m"),
    ("other_nc_liabilities", "Other non-current liabilities (plug)", "m"), ("total_liabilities", "Total liabilities", "m"),
    ("parent_equity", "Shareholders' equity (parent)", "m"), ("nci_equity", "Non-controlling interests", "m"),
    ("total_equity", "Total equity", "m"), ("total_le", "Total liabilities and equity", "m"),
    ("cfo", "Cash from operations", "m"), ("capex", "Capital expenditure", "m"), ("other_cfi", "Other investing (plug)", "m"),
    ("cfi", "Cash from investing", "m"), ("dividends", "Dividends paid", "m"), ("buybacks", "Share repurchases", "m"),
    ("other_cff", "Other financing (plug)", "m"), ("cff", "Cash from financing", "m"), ("fx_effect", "FX effect on cash", "m"),
    ("net_change_cash", "Net change in cash (CF basis)", "m"), ("stores", "Warehouses at year end", "n"),
]

DRIVER_HIST = {  # historical value of each driver, as a template (None = not defined for that column)
    "store_openings": (1, "={Hist.stores}-{Hist.stores@-1}"),
    "sales_per_store_growth": (2, "={Schedules.rev_per_store}/{Schedules.rev_per_store@-1}-1"),
    "gross_margin": (0, "=1-{Hist.cogs}/{Hist.revenue}"),
    "sga_pct": (0, "={Hist.sga}/{Hist.revenue}"),
    "other_opex_pct": (0, "={Hist.other_opex}/{Hist.revenue}"),
    "da_pct_ppe": (1, "={Hist.da}/{Hist.ppe_net@-1}"),
    "capex_pct": (0, "=-{Hist.capex}/{Hist.revenue}"),
    "tax_rate": (0, "={Hist.income_tax}/{Hist.pretax_income}"),
    "receivable_days": (0, "={Hist.receivables}/{Hist.revenue}*{Inputs.$days_in_year}"),
    "inventory_days": (0, "={Hist.inventory}/{Hist.cogs}*{Inputs.$days_in_year}"),
    "payable_days": (0, "={Hist.accounts_payable}/{Hist.cogs}*{Inputs.$days_in_year}"),
    "oca_pct": (0, "={Hist.other_current_assets}/{Hist.revenue}"),
    "ocl_pct": (0, "={BS.ocl}/{Hist.revenue}"),
    "sbc_pct": (0, "={Hist.sbc}/{Hist.revenue}"),
    "debt_rate": (1, "={Hist.interest_expense}/AVERAGE({BS.debt},{BS.debt@-1})"),
    "cash_rate": (1, "={Hist.other_nonop_income}/AVERAGE({Hist.cash},{Hist.cash@-1})"),
    "payout_ratio": (0, "=-{Hist.dividends}/{Hist.net_income}"),
    "buyback_pct": (0, "=-{Hist.buybacks}/{Hist.net_income}"),
    "share_price_growth": (None, None),
}

DRIVER_LABEL = {
    "store_openings": "Net warehouse openings", "sales_per_store_growth": "Revenue per avg. warehouse growth",
    "gross_margin": "Gross margin", "sga_pct": "SG&A % revenue", "other_opex_pct": "Other opex % revenue",
    "da_pct_ppe": "D&A % opening PP&E", "capex_pct": "Capex % revenue", "tax_rate": "Effective tax rate",
    "receivable_days": "Receivable days (revenue)", "inventory_days": "Inventory days (COGS)",
    "payable_days": "Payable days (COGS)", "oca_pct": "Other current assets % revenue",
    "ocl_pct": "Other current liabilities % revenue", "sbc_pct": "SBC % revenue", "debt_rate": "Interest rate on debt",
    "cash_rate": "Interest rate on cash", "payout_ratio": "Regular dividend payout", "buyback_pct": "Buybacks % net income",
    "share_price_growth": "Share price growth (for share count)",
}

CONST_LABEL = {
    "days_in_year": "Days in year", "min_cash": "Minimum cash balance", "max_cash": "Cash ceiling (excess paid as special dividend)",
    "revolver_capacity": "Revolver capacity", "revolver_rate": "Revolver interest rate", "refinance_pct": "Maturities refinanced",
}
CONST_FMT = {"days_in_year": "n", "min_cash": "m", "max_cash": "m", "revolver_capacity": "m", "revolver_rate": "pct",
             "refinance_pct": "pct"}


def timeline(inp: Inputs) -> Timeline:
    return Timeline(inp.period_ends(), inp.labels(), inp.n_hist)


def _hist_only(tmpl, first: int = 0):
    return lambda i: tmpl if i is not None and i >= first else None


def add_three_statement(m: Model, inp: Inputs, extra_checks: list | None = None) -> None:
    n_h = inp.n_hist
    m.iterate = True  # allows the circularity switch to be turned on in Excel

    # ---------------------------------------------------------------- Inputs
    s = m.sheet("Inputs", "Inputs and switches")
    s.section("Switches")
    s.add("scenario", "Live scenario (1 Base, 2 Upside, 3 Downside)", "count", const=inp.scenario, fmt="n",
          const_note="Scenario selector feeding every forecast driver via CHOOSE on the Drivers sheet.")
    s.add("scenario_name", "Live scenario name", "", const='=CHOOSE({$scenario},"Base","Upside","Downside")', fmt="text")
    s.add("circ", "Circularity switch (1 = interest on average balances)", "count", const=inp.circ, fmt="n",
          const_note="Circuit breaker (ADR 0006). 0 = interest on opening balances, no circular reference. "
                     "1 = average balances; requires iterative calculation (enabled in this file).")
    s.blank()
    s.section("Constants")
    for k, label in CONST_LABEL.items():
        s.add(k, label, inp.spec["constants"][k]["unit"], const=inp.constants[k], fmt=CONST_FMT[k],
              const_note=inp.notes[k])
    s.add("share_price", "Share price at snapshot", "$", const=inp.share_price, fmt="ps", const_note=inp.share_price_source)
    m.names["Scenario"] = f"'Inputs'!$C${s.row('scenario')}"
    m.names["CircSwitch"] = f"'Inputs'!$C${s.row('circ')}"

    # ---------------------------------------------------------------- Hist
    h = m.sheet("Hist", f"Historical financials: {inp.history.entity} (from 10-K XBRL)")
    h.section("Normalised history (fixtures/%s/history.csv). Blue = as filed; plugs make subtotals tie." % inp.ticker)
    hist_idx = list(inp.hist_slice)
    for key, label, fmt in HIST_ITEMS:
        vals = inp.h(key)
        r = h.add(key, label, "$m" if fmt in ("m",) else ("$" if fmt == "ps" else ("m" if fmt == "m1" else "count")),
                  hist=list(vals) + [None] * inp.n_fcst, style="input", fmt=fmt)
        srcs = [inp.history.source[key][i] for i in hist_idx]
        r.note = f"Source per year: " + "; ".join(f"{inp.labels()[j]}: {src}" for j, src in enumerate(srcs))

    # ---------------------------------------------------------------- Scenarios
    sc = m.sheet("Scenarios", "Scenario inputs by driver (blue = judgement, see notes)")
    for d, cases in inp.drivers.items():
        fmt = inp.spec["drivers"][d]["fmt"]
        sc.section(DRIVER_LABEL[d])
        for case in CASES:
            r = sc.add(f"{d}_{case}", f"  {CASE_LABEL[case]}", inp.spec["drivers"][d]["unit"],
                       fcst=[None] * n_h + list(cases[case]), style="input", fmt=fmt)
            if case == "base":
                r.note = inp.notes[d]

    # ---------------------------------------------------------------- Drivers (live)
    dv = m.sheet("Drivers", "Live drivers: history implied, forecast from the selected scenario")
    for d in inp.drivers:
        first, tmpl = DRIVER_HIST[d]
        hist = _hist_only(tmpl, first) if tmpl else None
        fcst = "=CHOOSE({Inputs.$scenario}," + ",".join("{Scenarios.%s_%s}" % (d, c) for c in CASES) + ")"
        dv.add(d, DRIVER_LABEL[d], inp.spec["drivers"][d]["unit"], hist=hist, fcst=fcst,
               fmt=inp.spec["drivers"][d]["fmt"])

    # ---------------------------------------------------------------- Schedules
    sd = m.sheet("Schedules", "Supporting schedules")
    sd.section("Revenue build")
    sd.add("stores", "Warehouses at year end", "count", hist="={Hist.stores}", fcst="={stores@-1}+{Drivers.store_openings}", fmt="n")
    sd.add("avg_stores", "Average warehouses", "count", hist=_hist_only("=AVERAGE({stores},{stores@-1})", 1),
           fcst="=AVERAGE({stores},{stores@-1})", fmt="n1")
    sd.add("rev_per_store", "Revenue per average warehouse", "$m", hist=_hist_only("={IS.revenue}/{avg_stores}", 1),
           fcst="={rev_per_store@-1}*(1+{Drivers.sales_per_store_growth})", fmt="m1")
    sd.add("revenue", "Revenue", "$m", hist="={Hist.revenue}", fcst="={avg_stores}*{rev_per_store}", style="total")
    sd.blank()
    sd.section("PP&E")
    sd.add("ppe_open", "Opening PP&E, net", "$m", fcst="={BS.ppe_net@-1}")
    sd.add("capex", "Capital expenditure", "$m", hist="=-{Hist.capex}", fcst="={IS.revenue}*{Drivers.capex_pct}")
    sd.add("da", "Depreciation and amortisation", "$m", hist="={Hist.da}", fcst="={Drivers.da_pct_ppe}*{ppe_open}")
    sd.add("ppe_close", "Closing PP&E, net", "$m", hist="={Hist.ppe_net}", fcst="={ppe_open}+{capex}-{da}", style="total")
    sd.blank()
    sd.section("Working capital")
    sd.add("receivables", "Receivables", "$m", hist="={Hist.receivables}",
           fcst="={IS.revenue}*{Drivers.receivable_days}/{Inputs.$days_in_year}")
    sd.add("inventory", "Inventory", "$m", hist="={Hist.inventory}",
           fcst="={IS.cogs}*{Drivers.inventory_days}/{Inputs.$days_in_year}")
    sd.add("other_current_assets", "Other current assets", "$m", hist="={Hist.other_current_assets}",
           fcst="={IS.revenue}*{Drivers.oca_pct}")
    sd.add("accounts_payable", "Accounts payable", "$m", hist="={Hist.accounts_payable}",
           fcst="={IS.cogs}*{Drivers.payable_days}/{Inputs.$days_in_year}")
    sd.add("ocl", "Other current liabilities", "$m", hist="={BS.ocl}", fcst="={IS.revenue}*{Drivers.ocl_pct}")
    sd.add("nwc", "Net working capital", "$m", all="={receivables}+{inventory}+{other_current_assets}-{accounts_payable}-{ocl}",
           style="total")
    sd.add("change_nwc", "Cash impact of working capital (increase = outflow)", "$m", fcst="={nwc@-1}-{nwc}")
    sd.add("sbc", "Stock-based compensation", "$m", hist="={Hist.sbc}", fcst="={IS.revenue}*{Drivers.sbc_pct}")
    sd.blank()
    sd.section("Debt and revolver")
    sd.add("debt_open", "Opening debt", "$m", fcst="={BS.debt@-1}")
    r = sd.add("maturities", "Scheduled maturities (10-K debt footnote)", "$m", fcst=[None] * n_h + list(inp.maturities),
               style="input")
    r.note = "Sources: " + "; ".join(f"{inp.labels()[n_h + k]}: {src}" for k, src in enumerate(inp.maturity_sources))
    sd.add("debt_repay", "Repayment", "$m", fcst="=MIN({maturities},{debt_open})")
    sd.add("debt_issue", "New issuance (refinancing)", "$m", fcst="={maturities}*{Inputs.$refinance_pct}")
    sd.add("debt_close", "Closing debt", "$m", hist="={BS.debt}", fcst="={debt_open}-{debt_repay}+{debt_issue}", style="total")
    sd.add("cash_avail", "Cash before special dividend and revolver", "$m",
           fcst="={BS.cash@-1}+{CF.cfo}+{CF.cfi}+{CF.dividends}+{CF.buybacks}+{debt_issue}-{debt_repay}")
    sd.add("special_div", "Special dividend (cash above ceiling)", "$m", fcst="=-MAX(0,{cash_avail}-{Inputs.$max_cash})")
    sd.add("cash_pre_rev", "Cash before revolver", "$m", fcst="={cash_avail}+{special_div}")
    sd.add("rev_open", "Opening revolver", "$m", fcst="={BS.revolver@-1}")
    sd.add("rev_draw", "Revolver draw / (repayment)", "$m",
           fcst="=MIN(MAX({Inputs.$min_cash}-{cash_pre_rev},-{rev_open}),{Inputs.$revolver_capacity}-{rev_open})")
    sd.add("rev_close", "Closing revolver", "$m", hist=0, fcst="={rev_open}+{rev_draw}", style="total")
    sd.add("debt_interest", "Interest on debt", "$m",
           fcst="={Drivers.debt_rate}*IF({Inputs.$circ}=1,AVERAGE({debt_open},{debt_close}),{debt_open})")
    sd.add("rev_interest", "Interest on revolver", "$m",
           fcst="={Inputs.$revolver_rate}*IF({Inputs.$circ}=1,AVERAGE({rev_open},{rev_close}),{rev_open})")
    sd.add("interest_income", "Interest income on cash", "$m",
           fcst="={Drivers.cash_rate}*IF({Inputs.$circ}=1,AVERAGE({BS.cash@-1},{BS.cash}),{BS.cash@-1})")
    sd.blank()
    sd.section("Equity and shares")
    sd.add("eq_open", "Opening parent equity", "$m", fcst="={BS.parent_equity@-1}")
    sd.add("eq_ni", "Net income to parent", "$m", fcst="={IS.net_income}")
    sd.add("eq_div", "Dividends (regular + special)", "$m", fcst="={CF.dividends}+{CF.special_dividends}")
    sd.add("eq_bb", "Share repurchases", "$m", fcst="={CF.buybacks}")
    sd.add("eq_sbc", "Stock-based compensation", "$m", fcst="={sbc}")
    sd.add("eq_close", "Closing parent equity", "$m", hist="={Hist.parent_equity}",
           fcst="={eq_open}+{eq_ni}+{eq_div}+{eq_bb}+{eq_sbc}", style="total")
    sd.add("share_price", "Assumed share price", "$", hist=[None] * (n_h - 1) + ["={Inputs.$share_price}"] + [None] * inp.n_fcst,
           fcst="={share_price@-1}*(1+{Drivers.share_price_growth})", fmt="ps")
    sd.add("shares", "Diluted shares", "m", hist="={Hist.shares_diluted}",
           fcst="={shares@-1}+({sbc}+{CF.buybacks})/{share_price}", fmt="m1")

    # ---------------------------------------------------------------- IS
    is_ = m.sheet("IS", "Income statement")
    is_.add("revenue", "Revenue", "$m", hist="={Hist.revenue}", fcst="={Schedules.revenue}", style="total")
    is_.add("cogs", "Cost of goods sold", "$m", hist="={Hist.cogs}", fcst="={revenue}*(1-{Drivers.gross_margin})")
    is_.add("gross_profit", "Gross profit", "$m", all="={revenue}-{cogs}", style="total")
    is_.add("sga", "SG&A", "$m", hist="={Hist.sga}", fcst="={revenue}*{Drivers.sga_pct}")
    is_.add("other_opex", "Other operating expense", "$m", hist="={Hist.other_opex}", fcst="={revenue}*{Drivers.other_opex_pct}")
    is_.add("operating_income", "Operating income (EBIT)", "$m", all="={gross_profit}-{sga}-{other_opex}", style="total")
    is_.add("interest_expense", "Interest expense", "$m", hist="={Hist.interest_expense}",
            fcst="={Schedules.debt_interest}+{Schedules.rev_interest}")
    is_.add("other_nonop_income", "Interest and other income", "$m", hist="={Hist.other_nonop_income}",
            fcst="={Schedules.interest_income}")
    is_.add("pretax_income", "Pre-tax income", "$m", all="={operating_income}-{interest_expense}+{other_nonop_income}", style="total")
    is_.add("income_tax", "Income tax", "$m", hist="={Hist.income_tax}", fcst="={pretax_income}*{Drivers.tax_rate}")
    is_.add("other_below_tax", "Other below tax", "$m", hist="={Hist.other_below_tax}", fcst=0)
    is_.add("net_income_total", "Net income incl. NCI", "$m", all="={pretax_income}-{income_tax}+{other_below_tax}", style="total")
    is_.add("nci_income", "NCI share", "$m", hist="={Hist.nci_income}", fcst=0)
    is_.add("net_income", "Net income to parent", "$m", all="={net_income_total}-{nci_income}", style="total")
    is_.blank()
    is_.add("shares_diluted", "Diluted shares", "m", hist="={Hist.shares_diluted}", fcst="={Schedules.shares}", fmt="m1")
    is_.add("eps_diluted", "Diluted EPS", "$", all="={net_income}/{shares_diluted}", fmt="ps")
    is_.blank()
    is_.add("da", "Memo: D&A (within COGS and SG&A)", "$m", hist="={Hist.da}", fcst="={Schedules.da}")
    is_.add("ebitda", "Memo: EBITDA", "$m", all="={operating_income}+{da}")

    # ---------------------------------------------------------------- BS
    bs = m.sheet("BS", "Balance sheet")
    bs.add("cash", "Cash and equivalents", "$m", hist="={Hist.cash}", fcst="={cash@-1}+{CF.net_change_cash}")
    bs.add("st_investments", "Short-term investments", "$m", hist="={Hist.st_investments}", fcst="={st_investments@-1}")
    bs.add("receivables", "Receivables", "$m", hist="={Hist.receivables}", fcst="={Schedules.receivables}")
    bs.add("inventory", "Inventory", "$m", hist="={Hist.inventory}", fcst="={Schedules.inventory}")
    bs.add("other_current_assets", "Other current assets", "$m", hist="={Hist.other_current_assets}",
           fcst="={Schedules.other_current_assets}")
    bs.add("total_current_assets", "Total current assets", "$m", all="=SUM({cash}:{other_current_assets})", style="total")
    bs.add("ppe_net", "PP&E, net", "$m", hist="={Hist.ppe_net}", fcst="={Schedules.ppe_close}")
    for k, label in (("op_lease_rou", "Operating lease ROU assets"), ("goodwill", "Goodwill"), ("intangibles", "Intangibles"),
                     ("other_nc_assets", "Other non-current assets")):
        bs.add(k, label, "$m", hist="={Hist.%s}" % k, fcst="={%s@-1}" % k)
    bs.add("total_assets", "Total assets", "$m", all="={total_current_assets}+SUM({ppe_net}:{other_nc_assets})", style="total")
    bs.blank()
    bs.add("accounts_payable", "Accounts payable", "$m", hist="={Hist.accounts_payable}", fcst="={Schedules.accounts_payable}")
    bs.add("ocl", "Accrued, deferred and other current liabilities", "$m",
           hist="={Hist.accrued_liabilities}+{Hist.employee_liabilities}+{Hist.deferred_revenue}+{Hist.other_current_liabilities}",
           fcst="={Schedules.ocl}")
    bs.add("debt", "Debt (current + long-term + short-term)", "$m",
           hist="={Hist.current_debt}+{Hist.lt_debt}+{Hist.short_term_debt}", fcst="={Schedules.debt_close}")
    bs.add("revolver", "Revolver", "$m", hist=0, fcst="={Schedules.rev_close}")
    bs.add("op_lease_liab", "Operating lease liabilities", "$m",
           hist="={Hist.op_lease_liab_current}+{Hist.op_lease_liab_noncurrent}", fcst="={op_lease_liab@-1}")
    bs.add("other_nc_liabilities", "Other non-current liabilities", "$m", hist="={Hist.other_nc_liabilities}",
           fcst="={other_nc_liabilities@-1}")
    bs.add("total_liabilities", "Total liabilities", "$m", all="=SUM({accounts_payable}:{other_nc_liabilities})", style="total")
    bs.add("parent_equity", "Shareholders' equity (parent)", "$m", hist="={Hist.parent_equity}", fcst="={Schedules.eq_close}")
    bs.add("nci_equity", "Non-controlling interests", "$m", hist="={Hist.nci_equity}", fcst="={nci_equity@-1}")
    bs.add("total_equity", "Total equity", "$m", all="={parent_equity}+{nci_equity}", style="total")
    bs.add("total_le", "Total liabilities and equity", "$m", all="={total_liabilities}+{total_equity}", style="total")
    bs.blank()
    bs.add("balance_check", "Balance check (assets - liabilities - equity)", "$m", all="={total_assets}-{total_le}", style="check")

    # ---------------------------------------------------------------- CF
    cf = m.sheet("CF", "Cash flow statement")
    cf.add("net_income_total", "Net income incl. NCI", "$m", all="={IS.net_income_total}")
    cf.add("da", "Depreciation and amortisation", "$m", all="={IS.da}")
    cf.add("sbc", "Stock-based compensation", "$m", hist="={Hist.sbc}", fcst="={Schedules.sbc}")
    cf.add("change_nwc", "Change in working capital", "$m", fcst="={Schedules.change_nwc}")
    cf.add("other_operating", "Other operating items", "$m", hist="={Hist.cfo}-{net_income_total}-{da}-{sbc}", fcst=0)
    cf.add("cfo", "Cash from operations", "$m", all="=SUM({net_income_total}:{other_operating})", style="total")
    cf.add("capex", "Capital expenditure", "$m", hist="={Hist.capex}", fcst="=-{Schedules.capex}")
    cf.add("other_investing", "Other investing", "$m", hist="={Hist.other_cfi}", fcst=0)
    cf.add("cfi", "Cash from investing", "$m", all="=SUM({capex}:{other_investing})", style="total")
    cf.add("dividends", "Regular dividends", "$m", hist="={Hist.dividends}",
           fcst="=-MAX(0,{IS.net_income})*{Drivers.payout_ratio}")
    cf.add("special_dividends", "Special dividends", "$m", hist=0, fcst="={Schedules.special_div}")
    cf.add("buybacks", "Share repurchases", "$m", hist="={Hist.buybacks}", fcst="=-MAX(0,{IS.net_income})*{Drivers.buyback_pct}")
    cf.add("debt_issued", "Debt issued", "$m", fcst="={Schedules.debt_issue}")
    cf.add("debt_repaid", "Debt repaid", "$m", fcst="=-{Schedules.debt_repay}")
    cf.add("revolver", "Revolver draw / (repayment)", "$m", fcst="={Schedules.rev_draw}")
    cf.add("other_financing", "Other financing", "$m", hist="={Hist.other_cff}", fcst=0)
    cf.add("cff", "Cash from financing", "$m", all="=SUM({dividends}:{other_financing})", style="total")
    cf.add("fx_effect", "FX effect on cash", "$m", hist="={Hist.fx_effect}", fcst=0)
    cf.add("net_change_cash", "Net change in cash", "$m", all="={cfo}+{cfi}+{cff}+{fx_effect}", style="total")
    cf.blank()
    cf.add("fcf", "Memo: free cash flow (CFO + capex)", "$m", all="={cfo}+{capex}")

    # ---------------------------------------------------------------- Ratios
    ra = m.sheet("Ratios", "Ratio analysis")
    ra.add("rev_growth", "Revenue growth", "%", hist=_hist_only("={IS.revenue}/{IS.revenue@-1}-1", 1),
           fcst="={IS.revenue}/{IS.revenue@-1}-1", fmt="pct")
    ra.add("gross_margin", "Gross margin", "%", all="={IS.gross_profit}/{IS.revenue}", fmt="pct")
    ra.add("ebit_margin", "EBIT margin", "%", all="={IS.operating_income}/{IS.revenue}", fmt="pct")
    ra.add("ebitda_margin", "EBITDA margin", "%", all="={IS.ebitda}/{IS.revenue}", fmt="pct")
    ra.add("net_margin", "Net margin", "%", all="={IS.net_income}/{IS.revenue}", fmt="pct")
    ra.add("eps_growth", "Diluted EPS growth", "%", hist=_hist_only("={IS.eps_diluted}/{IS.eps_diluted@-1}-1", 1),
           fcst="={IS.eps_diluted}/{IS.eps_diluted@-1}-1", fmt="pct")
    ra.add("roe", "Return on average equity", "%", hist=_hist_only("={IS.net_income}/AVERAGE({BS.parent_equity},{BS.parent_equity@-1})", 1),
           fcst="={IS.net_income}/AVERAGE({BS.parent_equity},{BS.parent_equity@-1})", fmt="pct")
    ra.add("net_debt", "Net debt / (net cash)", "$m", all="={BS.debt}+{BS.revolver}-{BS.cash}-{BS.st_investments}")
    ra.add("net_debt_ebitda", "Net debt / EBITDA", "x", all="={net_debt}/{IS.ebitda}", fmt="x")
    ra.add("interest_cover", "EBIT / interest expense", "x", all="={IS.operating_income}/{IS.interest_expense}", fmt="x")
    ra.add("fcf_conversion", "FCF / net income", "%", all="={CF.fcf}/{IS.net_income}", fmt="pct")

    # ---------------------------------------------------------------- Checks
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)")
    checks = [
        ("bs_balances", "Balance sheet balances", dict(all="={BS.balance_check}")),
        ("cash_ties", "BS cash change = CF net change (forecast)", dict(fcst="={BS.cash}-{BS.cash@-1}-{CF.net_change_cash}")),
        ("hist_cf_ties", "Historical CF components sum to reported change in cash", dict(hist="={CF.net_change_cash}-{Hist.net_change_cash}")),
        ("hist_ni_ties", "Historical net income = as filed", dict(hist="={IS.net_income}-{Hist.net_income}")),
        ("hist_ebit_ties", "Historical EBIT = as filed", dict(hist="={IS.operating_income}-{Hist.operating_income}")),
        ("hist_assets_tie", "Historical total assets = as filed", dict(hist="={BS.total_assets}-{Hist.total_assets}")),
        ("hist_liab_tie", "Historical total liabilities = as filed", dict(hist="={BS.total_liabilities}-{Hist.total_liabilities}")),
        ("revolver_cap", "Revolver within capacity", dict(fcst="=MAX(0,{BS.revolver}-{Inputs.$revolver_capacity})")),
        ("revolver_nonneg", "Revolver not negative", dict(fcst="=MIN(0,{BS.revolver})")),
        ("debt_nonneg", "Debt not negative", dict(fcst="=MIN(0,{BS.debt})")),
    ]
    checks += extra_checks or []
    for key, label, kw in checks:
        if "const" in kw:  # single-value check
            ck.add(key, label, "", style="check", **kw)
        else:
            ck.add(key, label, "$m", const="=SUMPRODUCT(ABS({%s:all}))" % key, style="check", **kw)
    ck.blank()
    ck.add("tolerance", "Tolerance", "$m", const=0.001, fmt="0.000")
    first, last = checks[0][0], checks[-1][0]
    ck.add("master", "MASTER CHECK (0 = all pass)", "count", const="=IF(SUM({$%s}:{$%s})<{$tolerance},0,1)" % (first, last),
           style="total", fmt="flag")
    m.names["MasterCheck"] = f"'Checks'!$C${ck.row('master')}"
