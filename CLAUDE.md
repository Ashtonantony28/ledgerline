# CLAUDE.md: conventions for Ledgerline

This file is the contract for anyone (human or agent) touching this repository.

## Prime directives

1. **Every change ships with a Verify command.** A PR description names the exact command that proves it
   works (a `pytest` selection, an audit run, the mutation test). If something cannot be verified yet, say so
   and name the milestone that will make it verifiable.
2. **The Python reference model is the golden model.** Every workbook output must match its reference in
   `python/ledgerline/ref/` within the ADR 0005 tolerances ($0.01 on currency, 1e-9 relative on ratios) on
   the committed fixtures. A mismatch is a bug in one of them; the fix says which. References are written
   from the model spec in `docs/models/`, never by reading the workbook's formulas.
3. **Every input is sourced.** Each blue cell carries a note: XBRL tag and accession, filing and page, or
   "Judgement" with a rationale (spec/<TICKER>.yaml holds the rationale for every driver).
4. **The master check is green at every commit.** CI fails when any Checks-sheet line is non-zero.
5. **Back-tests are honest.** When a model disagrees with what actually happened, show the gap and explain
   it; never tune assumptions to match.
6. **Data is never committed raw.** Download scripts and checksums are. Fixture snapshots under `fixtures/`
   are committed; regenerating one is a reviewed change, never a silent overwrite.

## Workbook house style (ADR 0001, enforced by `ledgerline.audit`)

- FAST standard. Sheet order: Cover, Inputs, data, Scenarios, Drivers, calculations, statements, Checks, Log.
- Blue on yellow = input, black = formula, green = direct link, grey shading = forecast columns.
- One formula per row across the forecast columns (and across the history columns).
- No numeric literals inside formulas except 0 and 1; constants live in labelled input cells.
- Functions from the allow-list only (`audit.ALLOWED_FUNCS`): LibreOffice-compatible, non-volatile.
  No OFFSET/INDIRECT, no LET/LAMBDA/XLOOKUP in calculation sheets (ADR 0007).
- Circularity only behind the circuit-breaker switch (ADR 0006).
- No external links: a workbook embeds the modules it needs (ADR 0003).

## Code standards

- Python 3.11+, `pytest -q` from the repo root. Generator code in `python/ledgerline/`.
- Sign convention (ADR 0002): income-statement expenses positive; cash-flow items carry cash sign.
- Model units: $ millions, shares in millions.

## ADRs

- Hard-to-reverse decisions get an ADR in `docs/adr/` from `0000-template.md`; immutable once Accepted;
  supersede with a new ADR. Reference ADR numbers in code comments and PR descriptions.

## Branch / PR discipline

- Never commit directly to the default branch. One logical change per PR.
- PR description: what changed, **Verify command**, ADRs touched, roadmap milestone.
- Red CI never merges. Commit messages explain *why*.
