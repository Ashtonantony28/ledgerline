# Desktop Excel check

Excel 16.0 (Microsoft 365 Click-to-Run build 16.0.20625.20108, x64) on Windows-11-10.0.26300-SP0, 2026-11-25.
Tolerance: numbers within max($0.005, 1e-09 relative); text equal. Workbooks opened read-only and never saved.

| Workbook | Formula cells | Compared | Differ | Largest difference | Master check (Excel) |
|---|---|---|---|---|---|
| 00_Data | 809 | 809 | 0 | 5.00e-12 | None |
| 01_COST_ThreeStatement | 1825 | 1825 | 0 | 4.66e-10 | 0.0 |
| 02_COST_Valuation | 2118 | 2118 | 0 | 4.66e-10 | 0.0 |
| 03_SKX_LBO | 623 | 623 | 0 | 5.09e-11 | 0.0 |
| 04_DKS_FL_MnA | 440 | 440 | 0 | 4.73e-11 | 0.0 |
| 05_Group_Close | 1228 | 1228 | 0 | 4.71e-13 | 0.0 |
| 06_FPA_Forecast | 2284 | 2284 | 0 | 3.64e-12 | 0.0 |
| 07_COST_ScenarioLab | 2198 | 2198 | 0 | 4.66e-10 | 0.0 |
| 09_Credit | 414 | 414 | 0 | 3.20e-10 | 0.0 |
| 08_Dashboard | 9 | 9 | 0 | 0.00e+00 | 0.0 |
| 01_COST_ThreeStatement_circ | 1825 | 0 | 0 | 0.00e+00 | **#VALUE!** (script printed None) |

**Result: FAIL** (1 problem). The script printed PASS, but the circuit-breaker variant's master check is `#VALUE!`, not 0. Every one of the 10 delivered workbooks matches LibreOffice: 0 differing cells, largest difference 4.66e-10. 00_Data has no `MasterCheck` name, so its `None` is expected.

## Notes on the run

- **Circuit-breaker variant (circ = 1) fails in Excel.** With iterative calculation on (200 iterations, max change 1e-9), `Checks!C21` (`MasterCheck`) evaluates to `#VALUE!`. Error cells after `CalculateFullRebuild` plus repeated `Calculate`: Schedules 138 (from J37:S55), IS 80, BS 90, CF 90, Ratios 70, Checks 45 (C9:C10, C16:C17, C21), and Cover 1 (B9). Forecast columns J:S are affected and the historical columns are not, which looks like an error seeded inside the interest/debt loop that iteration cannot clear. `CalculationState` stayed at 2 (pending). The plain workbook (circ = 0) gives `MasterCheck` = 0.
- **The script hides this.** xlwings returns Excel error values as `None`, and `excel()` counts a `None` master as a pass. The check should read errors as text (for example with xlwings' `err_to_str=True` option) and fail on anything other than 0.
- **The script needed a local patch to finish.** Excel refuses `Application.Iteration` while no workbook is open (`Unable to set the Iteration property of the Application class`). For this run I moved the `Iteration`/`MaxIterations`/`MaxChange` assignment to after `books.open`, and the `Iteration = False` reset to before `book.close()`. The patch was not committed, and `tools/excel_check.py` on the branch is unchanged.

## Monte Carlo runner

`python -m ledgerline.xl.montecarlo workbooks/07_COST_ScenarioLab.xlsx --trials 200`, exit code 0, about 87 s:

```
200 trials; largest |Excel - Python| = 3.64e-12 $/share
```

Afterwards the workbook was closed without saving, and its MD5 hash was unchanged.

## VBA

Skipped. Programmatic access to the VBA project is blocked on this machine ("Programmatic access to Visual Basic Project is not trusted"), and the Trust Center setting was left unchanged. `CloseChecklist` and `ReconPack` were not imported or run. The Power Query step is manual and was not attempted.

## Resolution of the circ = 1 failure (2026-11-25)

Follow-up runs (`docs/excel-check-circ-cold.md`) showed there is no faulty formula. A generated workbook stores no
cached values, so when it is opened with the switch already at 1, Excel's first pass over the interest/cash loop
produces `#VALUE!`. The error then circulates through all 21 loop cells, and iteration cannot clear it. Cycling the
ADR 0006 circuit breaker (switch to 0, calculate, back to 1) clears it. After the reset, the check passes with 0
error cells and master check 0, and the results converge: cash $20,000m at the ceiling, FY2027 NI $9,982.3m
against $9,985.6m with opening-balance interest.

The fixes:
- `tools/excel_check.py` now reads Excel errors as text, so any error fails the check.
- The checker sets iteration only once a workbook is open.
- The checker cycles the breaker by default. `--no-reset` reproduces the cold open.
- The delivered workbook ships with the switch at 0, and the generator keeps it that way. To use iterative
  interest, set Inputs!C12 to 1 in Excel. If errors ever appear, set it to 0, recalculate, and set it back to 1.
  That procedure is documented in `docs/models/three-statement.md`.
