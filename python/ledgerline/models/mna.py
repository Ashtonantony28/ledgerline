"""Workbook 04: DICK'S Sporting Goods / Foot Locker accretion-dilution (docs/models/mna.md). Reference: ref/mna.py."""
from __future__ import annotations

from ..build.grid import Model, Timeline
from .assumptions import CASES
from .mna_inputs import MnAInputs
from .three_statement import CASE_LABEL

HIST = [("revenue", "Revenue", "$m", "m"), ("operating_income", "Operating income (EBIT)", "$m", "m"),
        ("da", "Depreciation and amortisation", "$m", "m"), ("interest_expense", "Interest expense", "$m", "m"),
        ("net_income", "Net income", "$m", "m"), ("shares_diluted", "Diluted shares", "m", "m1"),
        ("eps_diluted", "Diluted EPS", "$", "ps"), ("cash", "Cash and equivalents", "$m", "m"),
        ("current_debt", "Current portion of long-term debt", "$m", "m"), ("lt_debt", "Long-term debt", "$m", "m"),
        ("goodwill", "Goodwill", "$m", "m"), ("intangibles", "Intangible assets", "$m", "m"),
        ("parent_equity", "Shareholders' equity", "$m", "m")]
TX_LABEL = {
    "offer_price": ("Cash consideration per Foot Locker share", "$", "ps"),
    "exchange_ratio": ("Stock consideration: DKS shares per Foot Locker share", "x", "0.0000"),
    "fl_shares": ("Foot Locker shares outstanding", "m", "m1"), "dks_held_fl": ("Foot Locker shares already held by DICK'S", "m", "m1"),
    "stake_carrying": ("Carrying value of DICK'S Foot Locker stake", "$m", "m1"),
    "awards_cash": ("Equity awards settled in cash", "$m", "m1"), "replaced_awards": ("Replaced awards (pre-combination value)", "$m", "m1"),
    "txn_costs": ("DICK'S transaction costs", "$m", "m1"), "severance": ("Executive severance (post-combination expense)", "$m", "m1"),
    "retention": ("Retention bonuses (post-combination expense)", "$m", "m1"),
    "seller_costs": ("Foot Locker transaction costs assumed", "$m", "m1"), "notes_rate": ("New senior notes coupon", "%", "pct"),
    "issuance_fee": ("Note issuance costs (% of principal)", "%", "pct"), "pf_tax_rate": ("Tax rate on pro forma adjustments", "%", "pct"),
    "synergy_low": ("Cost synergy target, low", "$m", "m1"), "synergy_high": ("Cost synergy target, high", "$m", "m1"),
    "ppe_stepup": ("PP&E step-up to fair value", "$m", "m1"), "intangibles_fv": ("Identified intangibles at fair value", "$m", "m1"),
    "finite_intangibles": ("of which finite-lived", "$m", "m1"), "lease_favourable": ("Favourable lease terms", "$m", "m1"),
    "notes_fv_adj": ("Fair-value discount on Foot Locker notes", "$m", "m1"),
    "fl_hist_amort": ("Foot Locker historical amortisation eliminated", "$m", "m1"),
}
J_LABEL = {
    "min_cash": ("Minimum combined cash at close", "$m", "m"), "cash_yield": ("Yield on cash", "%", "pct"),
    "ppe_life": ("PP&E step-up life", "years", "n1"), "finite_life": ("Finite intangibles life", "years", "n1"),
    "lease_life": ("Favourable lease amortisation period", "years", "n1"), "notes_life": ("Foot Locker notes remaining life", "years", "n1"),
    "issuance_term": ("Issuance cost amortisation term", "years", "n1"), "dks_tax_rate": ("DICK'S tax rate", "%", "pct"),
    "acc_year": ("Accretion test year (forecast year #)", "year #", "n"), "fl_tax_rate": ("Foot Locker tax rate", "%", "pct"),
}
DRIVER_LABEL = {"dks_revenue_growth": "DICK'S revenue growth", "dks_ebitda_margin": "DICK'S EBITDA margin",
                "dks_da_pct": "DICK'S D&A % revenue", "fl_da_pct": "Foot Locker D&A % revenue"}


def timeline(inp: MnAInputs) -> Timeline:
    return Timeline(inp.period_ends(), inp.labels(), inp.n_hist)


def _amort(step: str, life: str) -> str:
    """Straight line, stopping once fully amortised (non-integer lives end with a partial year)."""
    return f"=MAX(0,MIN({step}/{life},{step}-{step}/{life}*({{fcst_n}}-1)))"


def add_mna(m: Model, inp: MnAInputs) -> None:
    tl = m.timeline
    n_h, lh, lf = inp.n_hist, inp.n_hist - 1, tl.n - 1
    nf = [None] * inp.n_fcst
    I = lambda k: "{Inputs.$%s}" % k

    # ---------------------------------------------------------------- Inputs
    s = m.sheet("Inputs", "Inputs: transaction terms (sourced), judgement, switches")
    s.section("Switches")
    s.add("scenario", "Operating case (1 Base, 2 Upside, 3 Downside)", "count", const=inp.scenario, fmt="n")
    s.add("scenario_name", "Operating case name", "", const='=CHOOSE({$scenario},"Base","Upside","Downside")', fmt="text")
    s.add("structure", "Consideration mix (1 All cash, 2 All stock, 3 Actual election)", "count", const=inp.structure, fmt="n")
    s.add("structure_name", "Consideration mix name", "",
          const="=CHOOSE({$structure}," + ",".join(f'"{x}"' for x in inp.structure_names) + ")", fmt="text")
    s.add("pct_stock", "Live: share of Foot Locker holders taking stock", "%",
          const="=CHOOSE({$structure},{Scenarios.$pct_stock_1},{Scenarios.$pct_stock_2},{Scenarios.$pct_stock_3})", fmt="pct")
    s.add("dks_price", "Live: DKS share price for the stock consideration", "$",
          const="=CHOOSE({$structure},{Scenarios.$dks_price_1},{Scenarios.$dks_price_2},{Scenarios.$dks_price_3})", fmt="ps")
    s.add("syn_runrate", "Live: run-rate cost synergies", "$m",
          const="=CHOOSE({$scenario}," + ",".join("{Scenarios.$syn_%s}" % c for c in CASES) + ")", fmt="m1")
    s.blank()
    s.section("Transaction terms (proxy statement/prospectus, 424B3 2025-07-11)")
    for k, (label, unit, fmt) in TX_LABEL.items():
        s.add(k, label, unit, const=inp.tx[k], fmt=fmt, const_note=inp.src[k])
    s.blank()
    s.section("Judgement")
    for k, (label, unit, fmt) in J_LABEL.items():
        s.add(k, label, unit, const=inp.j[k], fmt=fmt, const_note=inp.src[k])
    s.add("price_step", "Sensitivity step: offer price", "$", const=2.0, fmt="ps", const_note="Judgement: grid step.")
    s.add("pct_step", "Sensitivity step: share taking stock", "%", const=0.25, fmt="pct", const_note="Judgement: grid step.")
    s.add("syn_step", "Sensitivity step: synergy realisation", "%", const=0.5, fmt="pct", const_note="Judgement: grid step.")
    s.blank()
    s.section("Synergy phasing and costs to achieve (judgement)")
    r = s.add("syn_phase", "Share of run-rate achieved", "%", fcst=[None] * n_h + inp.syn_phase, style="input", fmt="pct")
    r.note = inp.src["syn_phase"]
    r = s.add("syn_costs", "Integration costs (one-time, pre-tax)", "$m", fcst=[None] * n_h + inp.syn_costs, style="input", fmt="m1")
    r.note = inp.src["syn_costs"]

    # ---------------------------------------------------------------- History
    idx = list(inp.hist_slice)
    for sheet, h, getter in (("Hist_DKS", inp.acq, inp.ha), ("Hist_FL", inp.tgt, inp.ht)):
        hs = m.sheet(sheet, f"Historical financials: {h.entity} (10-K XBRL)")
        for key, label, unit, fmt in HIST:
            r = hs.add(key, label, unit, hist=getter(key) + nf, style="input", fmt=fmt)
            r.note = "Source per year: " + "; ".join(f"{inp.labels()[j]}: {h.source[key][i]}" for j, i in enumerate(idx))

    # ---------------------------------------------------------------- Scenarios
    sc = m.sheet("Scenarios", "Operating cases, Foot Locker projections, consideration structures")
    for d in inp.drivers:
        sc.section(DRIVER_LABEL[d])
        for case in CASES:
            r = sc.add(f"{d}_{case}", f"  {CASE_LABEL[case]}", "%", fcst=[None] * n_h + inp.drivers[d][case], style="input", fmt="pct")
            if case == "base":
                r.note = inp.src[d]
    for item, label in (("revenue", "Foot Locker revenue"), ("ebitda", "Foot Locker adjusted EBITDA")):
        sc.section(label)
        for case in CASES:
            r = sc.add(f"fl_{item}_{case}", f"  {CASE_LABEL[case]}", "$m", fcst=[None] * n_h + inp.fl_proj[case][item], style="input")
            r.note = inp.src[f"fl_proj_{case}"]
    sc.section("Run-rate cost synergies by case")
    for case in CASES:
        sc.add(f"syn_{case}", f"  {CASE_LABEL[case]}", "$m", const=inp.syn_runrate[case], fmt="m1", const_note=inp.src["syn_runrate"])
    sc.section("Consideration structures")
    for k, name in enumerate(inp.structure_names, start=1):
        sc.add(f"pct_stock_{k}", f"  {name}: share taking stock", "%", const=inp.structures["pct_stock"][k - 1], fmt="pct",
               const_note=inp.src["pct_stock"])
        sc.add(f"dks_price_{k}", f"  {name}: DKS share price", "$", const=inp.structures["dks_price"][k - 1], fmt="ps",
               const_note=inp.src["dks_price"])

    # ---------------------------------------------------------------- Drivers
    dv = m.sheet("Drivers", "Live drivers (implied history, selected case forecast)")
    hist_tmpl = {
        "dks_revenue_growth": lambda i: "={Hist_DKS.revenue}/{Hist_DKS.revenue@-1}-1" if i >= 1 else None,
        "dks_ebitda_margin": "=({Hist_DKS.operating_income}+{Hist_DKS.da})/{Hist_DKS.revenue}",
        "dks_da_pct": "={Hist_DKS.da}/{Hist_DKS.revenue}",
        "fl_da_pct": "={Hist_FL.da}/{Hist_FL.revenue}",
    }
    pick = lambda name: "=CHOOSE({Inputs.$scenario}," + ",".join("{Scenarios.%s_%s}" % (name, c) for c in CASES) + ")"
    for d in inp.drivers:
        dv.add(d, DRIVER_LABEL[d], "%", hist=hist_tmpl[d], fmt="pct", fcst=pick(d))
    dv.add("fl_revenue", "Foot Locker revenue", "$m", hist="={Hist_FL.revenue}", fcst=pick("fl_revenue"))
    dv.add("fl_ebitda", "Foot Locker EBITDA (history: EBIT + D&A; forecast: adjusted)", "$m",
           hist="={Hist_FL.operating_income}+{Hist_FL.da}", fcst=pick("fl_ebitda"))

    # ---------------------------------------------------------------- Transaction
    t = m.sheet("Transaction", "Consideration, sources and uses, purchase price allocation", timeline=True)
    t.section("Consideration")
    t.add("n", "Foot Locker shares acquired (excluding DICK'S stake)", "m", const=f"={I('fl_shares')}-{I('dks_held_fl')}", fmt="m1")
    t.add("new_shares", "New DKS shares issued", "m", const=f"={{$n}}*{I('pct_stock')}*{I('exchange_ratio')}", fmt="m1")
    t.add("cash_holders", "Cash to Foot Locker shareholders", "$m", const=f"={{$n}}*(1-{I('pct_stock')})*{I('offer_price')}")
    t.add("c_awards", "Equity awards settled in cash", "$m", const=f"={I('awards_cash')}")
    t.add("stock_value", "Stock consideration (at DKS price)", "$m", const=f"={{$new_shares}}*{I('dks_price')}")
    t.add("per_share_value", "Blended value per Foot Locker share", "$",
          const=f"={I('pct_stock')}*{I('exchange_ratio')}*{I('dks_price')}+(1-{I('pct_stock')})*{I('offer_price')}", fmt="ps")
    t.add("stake_fv", "Fair value of DICK'S existing stake", "$m", const=f"={I('dks_held_fl')}*{{$per_share_value}}")
    t.add("c_replaced", "Replaced awards (pre-combination value)", "$m", const=f"={I('replaced_awards')}")
    t.add("consideration", "Fair value of consideration transferred", "$m",
          const="={$cash_holders}+{$c_awards}+{$stock_value}+{$stake_fv}+{$c_replaced}", style="total")
    t.add("stake_gain", "Gain on remeasuring the existing stake", "$m", const=f"={{$stake_fv}}-{I('stake_carrying')}")
    t.blank()
    t.section("Uses of cash at close")
    t.add("u_cash", "Cash consideration and awards", "$m", const="={$cash_holders}+{$c_awards}")
    t.add("u_costs", "Transaction costs, severance, retention, seller costs", "$m",
          const=f"={I('txn_costs')}+{I('severance')}+{I('retention')}+{I('seller_costs')}")
    t.add("cash_uses", "Cash uses before financing costs", "$m", const="={$u_cash}+{$u_costs}")
    t.add("issuance_cost", "Note issuance costs", "$m", const=f"={{$new_debt}}*{I('issuance_fee')}")
    t.add("uses", "Total uses", "$m", const="={$cash_uses}+{$issuance_cost}", style="total")
    t.section("Sources")
    t.add("avail", "Cash available above the minimum", "$m",
          const="={Hist_DKS.cash#%d}+{Hist_FL.cash#%d}-%s" % (lh, lh, I("min_cash")))
    t.add("new_debt", "New senior notes", "$m", const=f"=MAX(0,({{$cash_uses}}-{{$avail}})/(1-{I('issuance_fee')}))")
    t.add("cash_used", "Balance-sheet cash used", "$m", const="={$cash_uses}+{$issuance_cost}-{$new_debt}")
    t.add("sources", "Total sources", "$m", const="={$new_debt}+{$cash_used}", style="total")
    t.add("cash_close", "Combined cash after close", "$m", const="={Hist_DKS.cash#%d}+{Hist_FL.cash#%d}-{$cash_used}" % (lh, lh))
    t.blank()
    t.section("Purchase price allocation (ASC 805, Foot Locker balance sheet at 1 Feb 2025)")
    t.add("book_equity", "Foot Locker shareholders' equity", "$m", const="={Hist_FL.parent_equity#%d}" % lh)
    t.add("less_gw", "Less existing goodwill", "$m", const="=-{Hist_FL.goodwill#%d}" % lh)
    t.add("less_ia", "Less existing intangibles", "$m", const="=-{Hist_FL.intangibles#%d}" % lh)
    t.add("tangible_book", "Tangible book value", "$m", const="={$book_equity}+{$less_gw}+{$less_ia}", style="total")
    t.add("p_ia", "Identified intangibles at fair value", "$m", const=f"={I('intangibles_fv')}")
    t.add("p_ppe", "PP&E step-up", "$m", const=f"={I('ppe_stepup')}")
    t.add("p_lease", "Favourable leases", "$m", const=f"={I('lease_favourable')}")
    t.add("p_notes", "Notes fair-value discount (lower liability)", "$m", const=f"={I('notes_fv_adj')}")
    t.add("dtl", "Deferred tax on the step-ups", "$m",
          const=f"={I('pf_tax_rate')}*({{$p_ppe}}+{{$p_ia}}+{{$less_ia}}+{{$p_lease}}+{{$p_notes}})")
    t.add("p_seller", "Foot Locker transaction costs assumed", "$m", const=f"={I('seller_costs')}")
    t.add("net_assets", "Fair value of net identifiable assets", "$m",
          const="={$tangible_book}+{$p_ia}+{$p_ppe}+{$p_lease}+{$p_notes}-{$dtl}-{$p_seller}", style="total")
    t.add("excess", "Consideration less net assets", "$m", const="={$consideration}-{$net_assets}")
    t.add("goodwill", "Goodwill", "$m", const="=MAX(0,{$excess})", style="total")
    t.add("bargain_gain", "Bargain purchase gain (if net assets exceed consideration)", "$m", const="=MAX(0,-{$excess})")
    t.blank()
    t.section("Valuation and credit at close")
    t.add("offer_equity", "Offer equity value (all Foot Locker shares at $24.00)", "$m", const=f"={I('fl_shares')}*{I('offer_price')}")
    t.add("fl_debt", "Foot Locker debt", "$m", const="={Hist_FL.current_debt#%d}+{Hist_FL.lt_debt#%d}" % (lh, lh))
    t.add("offer_ev", "Offer enterprise value", "$m", const="={$offer_equity}+{$fl_debt}-{Hist_FL.cash#%d}" % lh)
    t.add("ev_ebitda_ltm", "Offer EV / FY2024 EBITDA (GAAP EBIT + D&A)", "x",
          const="={$offer_ev}/({Hist_FL.operating_income#%d}+{Hist_FL.da#%d})" % (lh, lh), fmt="x")
    t.add("ev_ebitda_fwd", "Offer EV / FY2025 projected adjusted EBITDA", "x", const="={$offer_ev}/{Drivers.fl_ebitda#%d}" % n_h, fmt="x")
    t.add("dks_debt", "DICK'S debt", "$m", const="={Hist_DKS.current_debt#%d}+{Hist_DKS.lt_debt#%d}" % (lh, lh))
    t.add("pf_debt", "Pro forma debt (Foot Locker notes at fair value)", "$m", const="={$dks_debt}+{$fl_debt}-{$p_notes}+{$new_debt}")
    t.add("pf_net_debt", "Pro forma net debt", "$m", const="={$pf_debt}-{$cash_close}", style="total")

    # ---------------------------------------------------------------- Standalone
    sa = m.sheet("Standalone", "Standalone forecasts (no deal)")
    sa.section("DICK'S Sporting Goods")
    sa.add("dks_revenue", "Revenue", "$m", hist="={Hist_DKS.revenue}", fcst="={dks_revenue@-1}*(1+{Drivers.dks_revenue_growth})", style="total")
    sa.add("dks_ebitda", "EBITDA", "$m", hist="={Hist_DKS.operating_income}+{Hist_DKS.da}", fcst="={dks_revenue}*{Drivers.dks_ebitda_margin}")
    sa.add("dks_da", "D&A", "$m", hist="={Hist_DKS.da}", fcst="={dks_revenue}*{Drivers.dks_da_pct}")
    sa.add("dks_ebit", "EBIT", "$m", all="={dks_ebitda}-{dks_da}")
    sa.add("dks_interest", "Interest expense (notes held flat)", "$m", hist="={Hist_DKS.interest_expense}",
           fcst="={Hist_DKS.interest_expense#%d}" % lh)
    sa.add("dks_int_income", "Interest income on cash (cash held flat)", "$m", fcst="={Hist_DKS.cash#%d}*%s" % (lh, I("cash_yield")))
    sa.add("dks_pretax", "Pre-tax income", "$m", fcst="={dks_ebit}-{dks_interest}+{dks_int_income}")
    sa.add("dks_tax", "Income tax", "$m", fcst="={dks_pretax}*%s" % I("dks_tax_rate"))
    sa.add("dks_ni", "Net income", "$m", hist="={Hist_DKS.net_income}", fcst="={dks_pretax}-{dks_tax}", style="total")
    sa.add("dks_shares", "Diluted shares (held flat)", "m", hist="={Hist_DKS.shares_diluted}", fcst="={Hist_DKS.shares_diluted#%d}" % lh, fmt="m1")
    sa.add("eps_sa", "Standalone diluted EPS", "$", hist="={Hist_DKS.eps_diluted}", fcst="={dks_ni}/{dks_shares}", fmt="ps", style="total")
    sa.blank()
    sa.section("Foot Locker")
    sa.add("fl_revenue", "Revenue", "$m", all="={Drivers.fl_revenue}", style="total")
    sa.add("fl_ebitda", "EBITDA", "$m", all="={Drivers.fl_ebitda}")
    sa.add("fl_da", "D&A", "$m", hist="={Hist_FL.da}", fcst="={fl_revenue}*{Drivers.fl_da_pct}")
    sa.add("fl_interest", "Interest expense (notes held flat)", "$m", hist="={Hist_FL.interest_expense}",
           fcst="={Hist_FL.interest_expense#%d}" % lh)
    sa.add("fl_pretax", "Pre-tax income", "$m", fcst="={fl_ebitda}-{fl_da}-{fl_interest}")
    sa.add("fl_tax", "Income tax", "$m", fcst="={fl_pretax}*%s" % I("fl_tax_rate"))
    sa.add("fl_ni", "Net income", "$m", hist="={Hist_FL.net_income}", fcst="={fl_pretax}-{fl_tax}", style="total")

    # ---------------------------------------------------------------- Pro forma
    pf = m.sheet("ProForma", "Pro forma combined earnings, accretion / dilution, credit")
    pf.section("Pre-tax pro forma adjustments (+ adds to earnings)")
    pf.add("syn", "Cost synergies", "$m", fcst=f"={I('syn_runrate')}*{{Inputs.syn_phase}}")
    pf.add("dep_step", "Depreciation of PP&E step-up", "$m", fcst=_amort(I("ppe_stepup"), I("ppe_life")))
    pf.add("amort_int", "Amortisation of finite intangibles", "$m", fcst=_amort(I("finite_intangibles"), I("finite_life")))
    pf.add("lease_amort", "Amortisation of favourable leases", "$m", fcst=_amort(I("lease_favourable"), I("lease_life")))
    pf.add("notes_accr", "Accretion of Foot Locker notes discount", "$m", fcst=_amort(I("notes_fv_adj"), I("notes_life")))
    pf.add("fl_amort_elim", "Foot Locker historical amortisation eliminated", "$m", fcst=f"={I('fl_hist_amort')}")
    pf.add("new_int", "Interest on new senior notes", "$m", fcst=f"={{Transaction.$new_debt}}*{I('notes_rate')}")
    pf.add("iss_amort", "Amortisation of issuance costs", "$m", fcst=_amort("{Transaction.$issuance_cost}", I("issuance_term")))
    pf.add("lost_int", "Interest income forgone on cash used", "$m", fcst=f"={{Transaction.$cash_used}}*{I('cash_yield')}")
    pf.add("adj_pretax", "Net pre-tax adjustment", "$m",
           fcst="={syn}-{dep_step}-{amort_int}-{lease_amort}-{notes_accr}+{fl_amort_elim}-{new_int}-{iss_amort}-{lost_int}", style="total")
    pf.blank()
    pf.section("Pro forma earnings per share")
    pf.add("pf_ni_adj", "Pro forma net income, adjusted (excl. one-time items)", "$m",
           fcst=f"={{Standalone.dks_ni}}+{{Standalone.fl_ni}}+{{adj_pretax}}*(1-{I('pf_tax_rate')})", style="total")
    pf.add("close_items", "One-time at close: costs less stake and bargain gains (pre-tax)", "$m",
           fcst=f"=IF({{fcst_n}}=1,{I('txn_costs')}+{I('severance')}+{I('retention')}-{{Transaction.$stake_gain}}-{{Transaction.$bargain_gain}},0)")
    pf.add("integration", "Integration costs (pre-tax)", "$m", fcst="={Inputs.syn_costs}")
    pf.add("pf_ni_gaap", "Pro forma net income, GAAP", "$m", fcst=f"={{pf_ni_adj}}-({{close_items}}+{{integration}})*(1-{I('pf_tax_rate')})")
    pf.add("pf_shares", "Pro forma diluted shares", "m", fcst="={Standalone.dks_shares}+{Transaction.$new_shares}", fmt="m1")
    pf.add("eps_sa", "Standalone EPS", "$", fcst="={Standalone.eps_sa}", fmt="ps")
    pf.add("eps_adj", "Pro forma EPS, adjusted", "$", fcst="={pf_ni_adj}/{pf_shares}", fmt="ps", style="total")
    pf.add("eps_gaap", "Pro forma EPS, GAAP", "$", fcst="={pf_ni_gaap}/{pf_shares}", fmt="ps")
    pf.add("acc_adj", "Accretion / (dilution), adjusted", "%", fcst="={eps_adj}/{eps_sa}-1", fmt="pct", style="total")
    pf.add("acc_gaap", "Accretion / (dilution), GAAP", "%", fcst="={eps_gaap}/{eps_sa}-1", fmt="pct")
    pf.add("breakeven_syn", "Pre-tax synergies needed to break even (adjusted)", "$m",
           fcst=f"={{syn}}-({{pf_ni_adj}}-{{eps_sa}}*{{pf_shares}})/(1-{I('pf_tax_rate')})")
    pf.add("breakeven_fl_ni", "Foot Locker net income needed to break even (adjusted)", "$m",
           fcst="={Standalone.fl_ni}-({pf_ni_adj}-{eps_sa}*{pf_shares})")
    pf.add("pf_ni_pre_fin", "Adjusted net income before deal financing (sensitivity helper)", "$m",
           fcst=f"={{pf_ni_adj}}+({{new_int}}+{{iss_amort}}+{{lost_int}})*(1-{I('pf_tax_rate')})")
    pf.blank()
    pf.section("Credit (net debt held at the closing level)")
    pf.add("pf_ebitda", "Pro forma EBITDA (incl. synergies)", "$m", fcst="={Standalone.dks_ebitda}+{Standalone.fl_ebitda}+{syn}")
    pf.add("pf_leverage", "Pro forma net debt / EBITDA", "x", fcst="={Transaction.$pf_net_debt}/{pf_ebitda}", fmt="x")
    pf.add("sa_leverage", "DICK'S standalone net debt / EBITDA, first forecast year", "x",
           const="=({Transaction.$dks_debt}-{Hist_DKS.cash#%d})/{Standalone.dks_ebitda#%d}" % (lh, n_h), fmt="x")
    pf.blank()
    pf.section("Contribution analysis (first forecast year): DICK'S share")
    c1 = n_h
    pf.add("contrib_rev", "Revenue", "%",
           const="={Standalone.dks_revenue#%d}/({Standalone.dks_revenue#%d}+{Standalone.fl_revenue#%d})" % (c1, c1, c1), fmt="pct")
    pf.add("contrib_ebitda", "EBITDA", "%",
           const="={Standalone.dks_ebitda#%d}/({Standalone.dks_ebitda#%d}+{Standalone.fl_ebitda#%d})" % (c1, c1, c1), fmt="pct")
    pf.add("contrib_ni", "Net income", "%",
           const="={Standalone.dks_ni#%d}/({Standalone.dks_ni#%d}+{Standalone.fl_ni#%d})" % (c1, c1, c1), fmt="pct")
    pf.add("own_dks", "Pro forma ownership: DICK'S holders", "%", const="={Standalone.dks_shares#%d}/{pf_shares#%d}" % (c1, c1), fmt="pct")
    pf.add("own_fl", "Pro forma ownership: former Foot Locker holders", "%", const="={Transaction.$new_shares}/{pf_shares#%d}" % c1, fmt="pct")
    pf.blank()
    pf.section("Accretion test year (sensitivity anchor)")
    X = lambda row: "INDEX({%s:fcst},%s)" % (row, I("acc_year"))
    pf.add("x_pre_fin", "Adjusted net income before financing", "$m", const="=" + X("pf_ni_pre_fin"))
    pf.add("x_eps_sa", "Standalone EPS", "$", const="=" + X("eps_sa"), fmt="ps")
    pf.add("x_acc", "Accretion / (dilution), adjusted", "%", const="=" + X("acc_adj"), fmt="pct", style="total")

    # ---------------------------------------------------------------- Sensitivity
    g = m.sheet("Sensitivity", "Accretion sensitivities (adjusted EPS)", timeline=False)
    g.col_widths = {"A": 4, "B": 22, **{chr(ord("C") + k): 11 for k in range(5)}}
    ref = lambda sh, key: f"'{sh}'!$C${m.sheets[sh].row(key)}"
    N, ER, OP = ref("Transaction", "n"), ref("Inputs", "exchange_ratio"), ref("Inputs", "offer_price")
    FIX, AV, FEE = ref("Transaction", "u_costs"), ref("Transaction", "avail"), ref("Inputs", "issuance_fee")
    RATE, TERM, YLD, TAX = ref("Inputs", "notes_rate"), ref("Inputs", "issuance_term"), ref("Inputs", "cash_yield"), ref("Inputs", "pf_tax_rate")
    CORE, EPS = ref("ProForma", "x_pre_fin"), ref("ProForma", "x_eps_sa")
    SH = f"'Standalone'!${tl.col(n_h)}${m.sheets['Standalone'].row('dks_shares')}"
    AW = ref("Inputs", "awards_cash")
    g.cell("B3", "Accretion in the test year: offer price (down) x share of holders taking stock (across)", bold=True, size=12)
    g.cell("C5", 0, input=True, fmt="pct", note="Grid start: no holders take stock.")
    for a, b in zip("CDEF", "DEFG"):
        g.cell(f"{b}5", f"={a}5+{ref('Inputs', 'pct_step')}", fmt="pct", bold=True)
    g.cell("B8", f"={OP}", fmt="ps", bold=True)
    g.cell("B7", f"=B8-{ref('Inputs', 'price_step')}", fmt="ps", bold=True); g.cell("B6", f"=B7-{ref('Inputs', 'price_step')}", fmt="ps", bold=True)
    g.cell("B9", f"=B8+{ref('Inputs', 'price_step')}", fmt="ps", bold=True); g.cell("B10", f"=B9+{ref('Inputs', 'price_step')}", fmt="ps", bold=True)
    for rr in range(6, 11):
        for c in "CDEFG":
            uses = f"({N}*(1-{c}$5)*$B{rr}+{AW}+{FIX})"
            debt = f"MAX(0,({uses}-{AV})/(1-{FEE}))"
            fin = f"({debt}*{RATE}+{debt}*{FEE}/{TERM}+({uses}+{debt}*{FEE}-{debt})*{YLD})"
            g.cell(f"{c}{rr}", f"=({CORE}-{fin}*(1-{TAX}))/({SH}+{N}*{c}$5*{ER}*$B{rr}/{OP})/{EPS}-1", fmt="pct")
    g.cell("B13", "Accretion by forecast year (down) x synergy realisation (across)", bold=True, size=12)
    g.cell("C15", 0, input=True, fmt="pct", note="Grid start: no synergies.")
    for a, b in zip("CDE", "DEF"):
        g.cell(f"{b}15", f"={a}15+{ref('Inputs', 'syn_step')}", fmt="pct", bold=True)
    pfs = m.sheets["ProForma"]
    rng = lambda key: f"'ProForma'!${tl.col(n_h)}${pfs.row(key)}:${tl.col(lf)}${pfs.row(key)}"
    for k in range(inp.n_fcst):
        rr = 16 + k
        g.cell(f"B{rr}", k + 1, input=True, fmt="n", note="Forecast year # (1 = FY2025).")
        for c in "CDEF":
            g.cell(f"{c}{rr}", f"=(INDEX({rng('pf_ni_adj')},$B{rr})+({c}$15-1)*INDEX({rng('syn')},$B{rr})*(1-{TAX}))"
                               f"/INDEX({rng('pf_shares')},$B{rr})/INDEX({rng('eps_sa')},$B{rr})-1", fmt="pct")

    # ---------------------------------------------------------------- Checks
    ck = m.sheet("Checks", "Integrity checks (every line must be zero)")
    tax = I("pf_tax_rate")
    checks = [
        ("su_balance", "Sources = uses", dict(const="={Transaction.$sources}-{Transaction.$uses}")),
        ("ppa_ties", "Goodwill less bargain gain = consideration less net assets",
         dict(const="={Transaction.$goodwill}-{Transaction.$bargain_gain}-{Transaction.$consideration}+{Transaction.$net_assets}")),
        ("cash_floor", "Cash after close not below the minimum", dict(const="=MIN(0,ROUND({Transaction.$cash_close}-%s,{$dp}))" % I("min_cash"))),
        ("own_sum", "Ownership sums to 100%", dict(const="=ROUND({ProForma.$own_dks}+{ProForma.$own_fl}-1,{$dp})")),
        ("ni_recon", "Adjusted NI = combined pre-tax less combined tax",
         dict(fcst="={ProForma.pf_ni_adj}-(({Standalone.dks_pretax}+{Standalone.fl_pretax}+{ProForma.adj_pretax})"
                   "-({Standalone.dks_tax}+{Standalone.fl_tax}+{ProForma.adj_pretax}*%s))" % tax)),
        ("breakeven", "EPS at breakeven synergies = standalone EPS",
         dict(fcst="=ROUND(({ProForma.pf_ni_adj}+({ProForma.breakeven_syn}-{ProForma.syn})*(1-%s))/{ProForma.pf_shares}"
                   "-{ProForma.eps_sa},{$dp})" % tax)),
        ("grid_ties", "Synergy grid at 100% = accretion row",
         dict(fcst="=ROUND(INDEX('Sensitivity'!$E$16:$E$%d,{fcst_n})-{ProForma.acc_adj},{$dp})" % (15 + inp.n_fcst))),
    ]
    for key, label, kw in checks:
        if "const" in kw:
            ck.add(key, label, "", style="check", **kw)
        else:
            ck.add(key, label, "$m", const="=SUMPRODUCT(ABS({%s:all}))" % key, style="check", **kw)
    ck.blank()
    ck.add("dp", "Rounding precision for ratio checks (decimal places)", "count", const=9, fmt="n",
           const_note="ADR 0005: ratios agree to 1e-9; checks on ratios round away floating-point noise beyond that.")
    ck.add("tolerance", "Tolerance", "$m", const=0.001, fmt="0.000")
    ck.add("master", "MASTER CHECK (0 = all pass)", "count",
           const="=IF(SUMPRODUCT(ABS({$su_balance}:{$grid_ties}))<{$tolerance},0,1)", style="total", fmt="flag")
    m.names["MasterCheck"] = f"'Checks'!$C${ck.row('master')}"
