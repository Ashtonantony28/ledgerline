# 0007: Audit rules and the function allow-list

- **Status:** Accepted
- **Date:** 2026-11-19

## Context
LibreOffice 24.2 (the CI engine) returns #NAME? for LET and XLOOKUP; volatile functions (OFFSET, INDIRECT)
make models slow and hard to trace.

## Decision
Calculation sheets use only functions in `ledgerline.audit.audit.ALLOWED_FUNCS`: LibreOffice-compatible and
non-volatile. Modern Excel functions (LET, LAMBDA, XLOOKUP, dynamic arrays) may appear only on presentation
sheets that CI does not compare, and only once the Excel check runs in CI. High-severity audit findings fail
the build: error values, external links, literals in formulas other than 0/1, disallowed or volatile functions,
inconsistent formulas within a row's forecast or history region, and numeric hard-codes not styled as inputs.

## Consequences
Some formulas are longer than their LET equivalents. The plan's §4.1 mention of LET/LAMBDA is narrowed by this ADR.
