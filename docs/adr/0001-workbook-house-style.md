# 0001: Workbook house style (FAST + ICAEW checklist)

- **Status:** Accepted
- **Date:** 2026-11-19

## Context
Finance teams judge a model first by whether it can be audited quickly. Spreadsheet error studies (Panko)
show most large models contain material errors, usually from inconsistent formulas and buried constants.

## Decision
Follow the FAST standard with the ICAEW Financial Modelling Code as a checklist:
fixed sheet order (Cover, Inputs, data, Scenarios, Drivers, calculations, statements, Ratios, Checks, Log);
FAST layout on time-series sheets (A label, B unit, C constant, D spacer, E onward timeline; rows 4-7
timeline, forecast flag and counter); colour code blue-on-yellow inputs, black formulas, green links,
grey forecast shading; one formula per row per region; no literals in formulas other than 0 and 1;
every input sourced in a cell note; a Checks sheet feeding a master flag shown on the Cover.

## Consequences
The audit tool can enforce most of this mechanically (ADR 0007). Hand-polished sheets must still pass it.
