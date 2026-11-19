# 0003: Workbooks are generated from code, then polished; no external links

- **Status:** Accepted
- **Date:** 2026-11-19

## Context
Plan decision D3 chose a hybrid build. Pure hand-built workbooks cannot be reviewed as diffs or regression-
tested; pure generated ones can look machine-made.

## Decision
A Python generator (`ledgerline.build.grid`) writes structure, formulas, names and formatting. Model logic is
declared as row templates in `python/ledgerline/models/*.py`; analyst judgement lives in `spec/<TICKER>.yaml`.
The plan suggested a YAML spec for formulas too; we keep formulas as Python row declarations because they
need references across sheets and per-region templates, which YAML would turn into a second language. YAML
holds what an analyst edits (drivers, rationales, constants).

Workbooks are self-contained: a valuation or LBO workbook embeds the operating-model sheets it needs rather
than linking to another file. External links are an audit failure.

Every build writes `<name>.layout.json` (row positions) and the audit writes `<name>.formulas.txt`, a text
dump of every cell, so reviews diff text rather than binary .xlsx.

## Consequences
Rebuilding is deterministic. Manual polish (charts, layout) must be re-applied or encoded in the generator;
we encode it wherever possible.
