# 0002: Sign conventions and units

- **Status:** Accepted
- **Date:** 2026-11-19

## Decision
- Income statement: revenue and expenses are stored as positive numbers; subtotals subtract expenses.
- Cash flow: every item carries its cash sign (outflows negative): capex, dividends, buybacks are negative.
- Balance sheet: assets, liabilities and equity positive.
- Model units: $ millions; shares in millions; EPS and share prices in $.
- XBRL values that report outflows as positive payments (e.g. PaymentsToAcquirePropertyPlantAndEquipment)
  are flipped with `sign: -1` in the tag map.

## Consequences
Formulas read naturally (`=revenue-cogs`, `=cfo+cfi+cff`). The reference model uses the same signs.
