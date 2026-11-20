# Interface: fundamental_signals.csv (Ledgerline -> Tickforge)

Schema version 1.1. Producer: `python -m ledgerline.exports`. One row per company and fiscal year (the first year is
dropped: growth and averages need a prior year).

**Point-in-time caveat.** `available_from` is fiscal year end + 90 days, a conservative filing lag. The *values* are as last reported
in the fixtures, which can be a later filing than the original (see `source_accession`: COST FY2018 comes from a 2020 10-K). A strict
point-in-time test must either accept that restatement look-ahead or rebuild the panel from each original filing; Tickforge's
"backtests do not lie" rule means the caveat travels with any result.

| column | type | unit / definition |
|---|---|---|
| schema_version | str |  |
| ticker | str |  |
| fy_end | date | ISO 8601 |
| available_from | date | ISO 8601, fy_end + lag |
| revenue_growth | float | ratio |
| gross_margin | float | ratio |
| operating_margin | float | ratio |
| fcf_margin | float | ratio |
| accruals_ratio | float | (net income - CFO) / average total assets |
| roa | float | net income / average total assets |
| lease_adj_leverage | float | x |
| source_accession | str | accession of the filing that last reported revenue |
