"""Workbook 07: scenario and sensitivity lab on the Costco valuation (docs/models/lab.md).

The Lab sheet is the scenario manager: a stress-case selector plus manual shifts feed additive "live" shifts into
the operating drivers (Drivers sheet) and the DCF (WACC sheet), so the whole model moves. Tornado, spider and Monte
Carlo results need thousands of model runs, which Excel cannot do without data tables or macros, so the Python
reference produces them (seeded) and they are written here as sourced values; checks tie the live workbook to the
same reference at the base case and at the selected stress case.
"""
from __future__ import annotations

from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.series import SeriesLabel

from ..build.grid import Model

SRC = "Python reference ledgerline.ref.lab (full re-run of ref.three_statement + ref.dcf with these shifts); spec/LAB_COST.yaml."


def add_lab(m: Model, lab: dict, stress: int = 0, manual: dict[str, float] | None = None) -> None:
    sp, manual = lab["spec"], manual or {}
    keys = list(sp["drivers"])
    stresses = sp["stress"]

    # ---------------------------------------------------------------- Lab (scenario manager)
    s = m.sheet("Lab", "Scenario manager: stress-case selector and manual shifts (added to every forecast year)")
    s.section("Stress case")
    s.add("stress", "Stress case (0 = none; " + ", ".join(f"{k} {x['name']}" for k, x in enumerate(stresses, 1)) + ")", "count",
          const=stress, fmt="n", const_note="Selector: 0 leaves the live operating case unchanged.")
    s.add("stress_name", "Stress case name", "", const="=CHOOSE({$stress}+1,\"None\"," + ",".join(f'"{x["name"]}"' for x in stresses) + ")",
          fmt="text")
    s.blank()
    s.section("Manual shifts (additive; percentage points as decimals)")
    for k in keys:
        d = sp["drivers"][k]
        s.add(f"man_{k}", f"  {d['label']}", d["unit"], const=manual.get(k, 0.0), fmt="0.000" if d["unit"] == "pp" else "n1",
              const_note="Judgement: type a shift here to flex the model; 0 = none.")
    s.blank()
    for j, x in enumerate(stresses, 1):
        s.section(f"Stress case {j}: {x['name']}")
        for k in keys:
            s.add(f"s{j}_{k}", f"  {sp['drivers'][k]['label']}", sp["drivers"][k]["unit"], const=x["shifts"].get(k, 0.0),
                  fmt="0.000" if sp["drivers"][k]["unit"] == "pp" else "n1", const_note="Judgement: spec/LAB_COST.yaml stress cases.")
    s.blank()
    s.section("Live shifts (manual + selected stress case)")
    for k in keys:
        s.add(f"live_{k}", f"  {sp['drivers'][k]['label']}", sp["drivers"][k]["unit"],
              const="={$man_%s}+CHOOSE({$stress}+1,0,%s)" % (k, ",".join("{$s%d_%s}" % (j, k) for j in range(1, len(stresses) + 1))),
              fmt="0.000" if sp["drivers"][k]["unit"] == "pp" else "n1")
    s.add("manual_abs", "Sum of absolute manual shifts", "", const="=SUMPRODUCT(ABS({$man_%s}:{$man_%s}))" % (keys[0], keys[-1]), fmt="0.000")
    s.blank()
    s.section("Live valuation")
    s.add("live_price_g", "Implied price: perpetuity growth", "$", const="={DCF.$price_g}", fmt="ps", style="total")
    s.add("live_price_x", "Implied price: exit multiple", "$", const="={DCF.$price_x}", fmt="ps", style="total")
    s.add("market", "Market price", "$", const="={WACC.$price}", fmt="ps")
    s.blank()
    s.section("Reference results (Python, for the ties on the Checks sheet)")
    s.add("py_base_g", "Base: perpetuity growth price", "$", const=lab["base"][0], fmt="ps", const_note=SRC)
    s.add("py_base_x", "Base: exit multiple price", "$", const=lab["base"][1], fmt="ps", const_note=SRC)
    for j, x in enumerate(lab["stress"], 1):
        s.add(f"py_s{j}_g", f"{x['name']}: perpetuity growth price", "$", const=x["price"][0], fmt="ps", const_note=SRC)
    for j, x in enumerate(lab["stress"], 1):
        s.add(f"py_s{j}_x", f"{x['name']}: exit multiple price", "$", const=x["price"][1], fmt="ps", const_note=SRC)
    nS = len(stresses)

    # ---------------------------------------------------------------- Tornado
    t = m.sheet("Tornado", "Tornado: implied price (perpetuity growth) with each driver moved one step down and up", timeline=False)
    t.col_widths = {"A": 30, "B": 10, "C": 15, "D": 15, "E": 15, "F": 15, "G": 12, "H": 12}
    t.cell("A3", "Base price ($/share)"); t.cell("C3", "='Lab'!$C$%d" % s.row("py_base_g"), fmt="ps")
    heads = ["Driver", "Step", "Price, step down", "Price, step up", "Change, down", "Change, up", "Swing"]
    for c, h in zip("ABCDEFG", heads):
        t.cell(f"{c}5", h, bold=True)
    for r, x in enumerate(lab["tornado"], start=6):
        t.cell(f"A{r}", x["label"])
        t.cell(f"B{r}", x["step"], input=True, fmt="0.000" if sp["drivers"][x["key"]]["unit"] == "pp" else "n1",
               note=sp["drivers"][x["key"]]["why"])
        t.cell(f"C{r}", x["low"][0], input=True, fmt="ps", note=SRC)
        t.cell(f"D{r}", x["high"][0], input=True, fmt="ps", note=SRC)
        t.cell(f"E{r}", f"=C{r}-$C$3", fmt="ps"); t.cell(f"F{r}", f"=D{r}-$C$3", fmt="ps")
        t.cell(f"G{r}", f"=ABS(F{r}-E{r})", fmt="ps")
    t_last = 5 + len(lab["tornado"])

    def tornado_chart(ws):
        ch = BarChart()
        ch.type, ch.grouping, ch.overlap = "bar", "clustered", 100
        ch.title = "Change in implied price from one step down / up ($/share)"
        ch.add_data(Reference(ws, min_col=5, max_col=6, min_row=5, max_row=t_last), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=6, max_row=t_last))
        ch.x_axis.scaling.orientation = "maxMin"  # largest swing on top; value axis keeps down-left, up-right
        ch.x_axis.tickLblPos = "low"  # driver names beside the axis, not over the bars
        ch.height, ch.width = 9, 18
        ws.add_chart(ch, f"A{t_last + 3}")

    # ---------------------------------------------------------------- Spider
    sd = m.sheet("Spider", "Spider: implied price (perpetuity growth) as each driver moves -2 to +2 steps", timeline=False)
    sd.col_widths = {"A": 30, **{c: 12 for c in "BCDEF"}}
    steps = sp["spider_steps"]
    sd.cell("A4", "Driver / steps", bold=True)
    for j, st in enumerate(steps):
        sd.cell(f"{'BCDEF'[j]}4", st, input=True, fmt="0", note="Judgement: spec/LAB_COST.yaml spider_steps.")
    for r, k in enumerate(keys, start=5):
        sd.cell(f"A{r}", sp["drivers"][k]["label"])
        for j, val in enumerate(lab["spider"][k]):
            sd.cell(f"{'BCDEF'[j]}{r}", val[0], input=True, fmt="ps", note=SRC)
    sp_last = 4 + len(keys)

    def spider_chart(ws):
        ch = LineChart()
        ch.title, ch.y_axis.title, ch.x_axis.title = "Implied price by driver step ($/share)", "$/share", "Steps"
        for r in range(5, sp_last + 1):
            ch.add_data(Reference(ws, min_col=2, max_col=6, min_row=r), from_rows=True, titles_from_data=False)
            ch.series[-1].tx = SeriesLabel(v=ws[f"A{r}"].value)
            ch.series[-1].smooth = False
        ch.set_categories(Reference(ws, min_col=2, max_col=6, min_row=4))
        ch.height, ch.width = 9, 18
        ws.add_chart(ch, f"A{sp_last + 3}")

    # ---------------------------------------------------------------- Monte Carlo
    mc = m.sheet("MonteCarlo", "Monte Carlo: distribution of implied price from simultaneous driver shifts (seeded)", timeline=False)
    mc.col_widths = {"A": 40, "B": 18, "C": 18, "D": 14, "E": 14}
    res = lab["mc"]
    mc.cell("A3", "Trials"); mc.cell("B3", res["trials"], input=True, fmt="n", note=SRC)
    mc.cell("A4", "Seed"); mc.cell("B4", res["seed"], input=True, fmt="n", note=SRC + " Same seed, same numbers.")
    mc.cell("A5", "Shifts: normal, standard deviation = one tornado step; sales growth and openings correlated 0.5", italic=True)
    mc.cell("A7", "Statistic", bold=True); mc.cell("B7", "Perpetuity growth", bold=True); mc.cell("C7", "Exit multiple", bold=True)
    rows = [("Mean", "mean")] + [(f"P{int(q * 100)}", q) for q in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)] + \
           [("Probability above the market price", "prob")]
    for r, (label, key) in enumerate(rows, start=8):
        mc.cell(f"A{r}", label)
        for col, meth in (("B", "gordon"), ("C", "exit")):
            v = res[meth]["mean"] if key == "mean" else res[meth]["prob_above_market"] if key == "prob" else res[meth]["p"][key]
            mc.cell(f"{col}{r}", v, input=True, fmt="pct" if key == "prob" else "ps", note=SRC)
    r_prob = 7 + len(rows)
    mc.cell(f"A{r_prob + 1}", "Market price"); mc.cell(f"B{r_prob + 1}", "='Lab'!$C$%d" % s.row("market"), fmt="ps")
    h0 = r_prob + 4
    mc.cell(f"A{h0}", "Histogram (perpetuity growth)", bold=True)
    for c, h in zip("ABCDE", ["Bin", "From", "To", "Trials", "Share"]):
        mc.cell(f"{c}{h0 + 1}", h, bold=True)
    edges, counts = res["gordon"]["edges"], res["gordon"]["counts"]
    for b, n in enumerate(counts):
        r = h0 + 2 + b
        mc.cell(f"B{r}", edges[b], input=True, fmt="ps", note=SRC)
        mc.cell(f"C{r}", edges[b + 1], input=True, fmt="ps", note=SRC)
        mc.cell(f"A{r}", f"=TEXT(AVERAGE(B{r},C{r}),\"#,##0\")")
        mc.cell(f"D{r}", n, input=True, fmt="n", note=SRC)
        mc.cell(f"E{r}", f"=D{r}/$B$3", fmt="pct")
    h_last = h0 + 1 + len(counts)

    def hist_chart(ws):
        ch = BarChart()
        ch.title, ch.y_axis.title = "Distribution of implied price, perpetuity growth ($/share)", "Trials"
        ch.add_data(Reference(ws, min_col=4, min_row=h0 + 2, max_row=h_last), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=1, min_row=h0 + 2, max_row=h_last))
        ch.gapWidth, ch.legend = 10, None
        ch.height, ch.width = 9, 18
        ws.add_chart(ch, "G3")

    m.charts = getattr(m, "charts", []) + [("Tornado", tornado_chart), ("Spider", spider_chart), ("MonteCarlo", hist_chart)]
    m.lab_checks = [
        ("lab_base_tie", "Live price = reference at the base case (no shifts)",
         dict(const="=IF(AND({Lab.$stress}=0,{Lab.$manual_abs}=0),ABS({Lab.$live_price_g}-{Lab.$py_base_g})"
                    "+ABS({Lab.$live_price_x}-{Lab.$py_base_x}),0)")),
        ("lab_stress_tie", "Live price = reference at the selected stress case",
         dict(const="=IF(AND({Lab.$stress}>0,{Lab.$manual_abs}=0),ABS({Lab.$live_price_g}-INDEX({Lab.$py_s1_g}:{Lab.$py_s%d_g},{Lab.$stress}))"
                    "+ABS({Lab.$live_price_x}-INDEX({Lab.$py_s1_x}:{Lab.$py_s%d_x},{Lab.$stress})),0)" % (nS, nS))),
        ("mc_trials", "Histogram counts sum to the trials",
         dict(const="=SUM('MonteCarlo'!$D$%d:$D$%d)-'MonteCarlo'!$B$3" % (h0 + 2, h_last))),
    ]
