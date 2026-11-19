# Known calculation-engine differences

| Area | LibreOffice 24.2 (CI) | `formulas` (CI, second engine) | Excel 365 | Handling |
|---|---|---|---|---|
| LET, LAMBDA, XLOOKUP | #NAME? | partial | supported | Not used in calculation sheets (ADR 0007) |
| Circular references (Inputs!circ = 1) | headless convert does not iterate to convergence | breaks the cycle with #CIRC! instead of iterating | iterates (file saved with iteration on) | CI tests circ = 0 on both engines; circ = 1 checked against the reference fixed point and in Excel before release (ADR 0006) |
| Static circularity with the breaker off | evaluates lazily, fine | needs `circular=True` to load (the IF branch is not taken but the graph has a cycle) | fine | `FormulasValues` always loads with `circular=True` |
