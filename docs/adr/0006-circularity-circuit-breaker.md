# 0006: Interest circularity behind a circuit breaker

- **Status:** Accepted
- **Date:** 2026-11-19

## Decision
Interest on debt, revolver and cash uses opening balances when `Inputs!circ = 0` (default) and average
balances when `circ = 1`. Average balances create a circular reference (interest -> net income -> cash ->
interest), so files are saved with iterative calculation enabled. The default build ships with the breaker
off, so a fresh file always calculates without iteration.

The reference model solves circ = 1 as a fixed point (tolerance 1e-10). LibreOffice headless does not iterate
this model to convergence and `formulas` breaks cycles rather than iterating (docs/known-differences.md),
so circ = 1 is verified against Excel before release.

## Consequences
A user can flip the switch in Excel to see the average-balance result; if iteration ever blows up, setting it
back to 0 recovers the model.
