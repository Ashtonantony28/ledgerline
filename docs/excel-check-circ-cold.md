# Desktop Excel check

Excel 16.0 on Windows-11-10.0.26300-SP0, 2026-11-25.
Tolerance: numbers within max($0.005, 1e-09 relative); text equal. Workbooks opened read-only and never saved.

| Workbook | Formula cells | Compared | Differ | Largest difference | Master check (Excel) |
|---|---|---|---|---|---|
| 01_COST_ThreeStatement_circ | 1825 | 0 | 514 | 0.00e+00 | #VALUE! |

**Result: FAIL** (515 problems).

## Differences (first 60)

- 01_COST_ThreeStatement_circ Cover!B9: Excel #VALUE! (`=IF(MasterCheck=0,"ALL CHECKS PASS","CHECK FAILURE - see Checks sheet")`)
- 01_COST_ThreeStatement_circ Schedules!J37: Excel #VALUE! (`=BS!I9+CF!J14+CF!J17+CF!J18+CF!J20+J35-J34`)
- 01_COST_ThreeStatement_circ Schedules!K37: Excel #VALUE! (`=BS!J9+CF!K14+CF!K17+CF!K18+CF!K20+K35-K34`)
- 01_COST_ThreeStatement_circ Schedules!L37: Excel #VALUE! (`=BS!K9+CF!L14+CF!L17+CF!L18+CF!L20+L35-L34`)
- 01_COST_ThreeStatement_circ Schedules!M37: Excel #VALUE! (`=BS!L9+CF!M14+CF!M17+CF!M18+CF!M20+M35-M34`)
- 01_COST_ThreeStatement_circ Schedules!N37: Excel #VALUE! (`=BS!M9+CF!N14+CF!N17+CF!N18+CF!N20+N35-N34`)
- 01_COST_ThreeStatement_circ Schedules!O37: Excel #VALUE! (`=BS!N9+CF!O14+CF!O17+CF!O18+CF!O20+O35-O34`)
- 01_COST_ThreeStatement_circ Schedules!P37: Excel #VALUE! (`=BS!O9+CF!P14+CF!P17+CF!P18+CF!P20+P35-P34`)
- 01_COST_ThreeStatement_circ Schedules!Q37: Excel #VALUE! (`=BS!P9+CF!Q14+CF!Q17+CF!Q18+CF!Q20+Q35-Q34`)
- 01_COST_ThreeStatement_circ Schedules!R37: Excel #VALUE! (`=BS!Q9+CF!R14+CF!R17+CF!R18+CF!R20+R35-R34`)
- 01_COST_ThreeStatement_circ Schedules!S37: Excel #VALUE! (`=BS!R9+CF!S14+CF!S17+CF!S18+CF!S20+S35-S34`)
- 01_COST_ThreeStatement_circ Schedules!J38: Excel #VALUE! (`=-MAX(0,J37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!K38: Excel #VALUE! (`=-MAX(0,K37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!L38: Excel #VALUE! (`=-MAX(0,L37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!M38: Excel #VALUE! (`=-MAX(0,M37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!N38: Excel #VALUE! (`=-MAX(0,N37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!O38: Excel #VALUE! (`=-MAX(0,O37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!P38: Excel #VALUE! (`=-MAX(0,P37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!Q38: Excel #VALUE! (`=-MAX(0,Q37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!R38: Excel #VALUE! (`=-MAX(0,R37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!S38: Excel #VALUE! (`=-MAX(0,S37-Inputs!$C$17)`)
- 01_COST_ThreeStatement_circ Schedules!J39: Excel #VALUE! (`=J37+J38`)
- 01_COST_ThreeStatement_circ Schedules!K39: Excel #VALUE! (`=K37+K38`)
- 01_COST_ThreeStatement_circ Schedules!L39: Excel #VALUE! (`=L37+L38`)
- 01_COST_ThreeStatement_circ Schedules!M39: Excel #VALUE! (`=M37+M38`)
- 01_COST_ThreeStatement_circ Schedules!N39: Excel #VALUE! (`=N37+N38`)
- 01_COST_ThreeStatement_circ Schedules!O39: Excel #VALUE! (`=O37+O38`)
- 01_COST_ThreeStatement_circ Schedules!P39: Excel #VALUE! (`=P37+P38`)
- 01_COST_ThreeStatement_circ Schedules!Q39: Excel #VALUE! (`=Q37+Q38`)
- 01_COST_ThreeStatement_circ Schedules!R39: Excel #VALUE! (`=R37+R38`)
- 01_COST_ThreeStatement_circ Schedules!S39: Excel #VALUE! (`=S37+S38`)
- 01_COST_ThreeStatement_circ Schedules!K40: Excel #VALUE! (`=BS!J25`)
- 01_COST_ThreeStatement_circ Schedules!L40: Excel #VALUE! (`=BS!K25`)
- 01_COST_ThreeStatement_circ Schedules!M40: Excel #VALUE! (`=BS!L25`)
- 01_COST_ThreeStatement_circ Schedules!N40: Excel #VALUE! (`=BS!M25`)
- 01_COST_ThreeStatement_circ Schedules!O40: Excel #VALUE! (`=BS!N25`)
- 01_COST_ThreeStatement_circ Schedules!P40: Excel #VALUE! (`=BS!O25`)
- 01_COST_ThreeStatement_circ Schedules!Q40: Excel #VALUE! (`=BS!P25`)
- 01_COST_ThreeStatement_circ Schedules!R40: Excel #VALUE! (`=BS!Q25`)
- 01_COST_ThreeStatement_circ Schedules!S40: Excel #VALUE! (`=BS!R25`)
- 01_COST_ThreeStatement_circ Schedules!J41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-J39,-J40),Inputs!$C$18-J40)`)
- 01_COST_ThreeStatement_circ Schedules!K41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-K39,-K40),Inputs!$C$18-K40)`)
- 01_COST_ThreeStatement_circ Schedules!L41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-L39,-L40),Inputs!$C$18-L40)`)
- 01_COST_ThreeStatement_circ Schedules!M41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-M39,-M40),Inputs!$C$18-M40)`)
- 01_COST_ThreeStatement_circ Schedules!N41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-N39,-N40),Inputs!$C$18-N40)`)
- 01_COST_ThreeStatement_circ Schedules!O41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-O39,-O40),Inputs!$C$18-O40)`)
- 01_COST_ThreeStatement_circ Schedules!P41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-P39,-P40),Inputs!$C$18-P40)`)
- 01_COST_ThreeStatement_circ Schedules!Q41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-Q39,-Q40),Inputs!$C$18-Q40)`)
- 01_COST_ThreeStatement_circ Schedules!R41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-R39,-R40),Inputs!$C$18-R40)`)
- 01_COST_ThreeStatement_circ Schedules!S41: Excel #VALUE! (`=MIN(MAX(Inputs!$C$16-S39,-S40),Inputs!$C$18-S40)`)
- 01_COST_ThreeStatement_circ Schedules!J42: Excel #VALUE! (`=J40+J41`)
- 01_COST_ThreeStatement_circ Schedules!K42: Excel #VALUE! (`=K40+K41`)
- 01_COST_ThreeStatement_circ Schedules!L42: Excel #VALUE! (`=L40+L41`)
- 01_COST_ThreeStatement_circ Schedules!M42: Excel #VALUE! (`=M40+M41`)
- 01_COST_ThreeStatement_circ Schedules!N42: Excel #VALUE! (`=N40+N41`)
- 01_COST_ThreeStatement_circ Schedules!O42: Excel #VALUE! (`=O40+O41`)
- 01_COST_ThreeStatement_circ Schedules!P42: Excel #VALUE! (`=P40+P41`)
- 01_COST_ThreeStatement_circ Schedules!Q42: Excel #VALUE! (`=Q40+Q41`)
- 01_COST_ThreeStatement_circ Schedules!R42: Excel #VALUE! (`=R40+R41`)
- 01_COST_ThreeStatement_circ Schedules!S42: Excel #VALUE! (`=S40+S41`)

## Same variant with the circuit-breaker reset (`excel --circ-only`, exit 0)

| Workbook | Formula cells | Compared | Differ | Largest difference | Master check (Excel) |
|---|---|---|---|---|---|
| 01_COST_ThreeStatement_circ | 1825 | 0 | 0 | 0.00e+00 | 0.0 |

**Result: PASS** (0 problems). When `Inputs!C12` goes to 0, Excel recalculates, and it goes back to 1, iteration converges with no error cells. Iteration was 200 and max change 1e-9.

## Root-cause diagnosis (Excel 16.0.20625.20108)

Cold start means: open read-only, turn Iteration on (200, 1e-9), then `CalculateFull` with no breaker reset. In that state there are 21 error cells in the column-J loop: Schedules J37-J39, J41, J42, J44, J45; IS J16-J18, J20, J22; CF J9, J14, J18-J20, J23, J25, J27; and BS J9.

**No root cell exists.** Every error cell in the loop has at least one error precedent, so `#VALUE!` keeps itself going around the cycle instead of starting from one non-error input:

- Schedules J37 `=BS!I9+CF!J14+CF!J17+CF!J18+CF!J20+J35-J34` takes errors from CF J14, J18 and J20.
- Schedules J38, J39, J41, J42 and J44 each take errors from the cell before them in the revolver chain.
- Schedules J45 `=Drivers!J24*IF(Inputs!$C$12=1,AVERAGE(BS!I9,BS!J9),BS!I9)` takes an error from BS J9.
- IS J16 (`=Schedules!J45`) feeds J17, J18, J20 and J22.
- CF J18 (`=-MAX(0,IS!J22)*Drivers!J25`) feeds CF J27, which feeds BS J9 (`=I9+CF!J27`), which feeds back into Schedules J45 and J37.

Schedules J43 (`=Drivers!J23*IF(Inputs!$C$12=1,AVERAGE(J32,J36),J32)`) stays numeric at 149.538, because it sits outside the error path. The file stores no cached values for the loop cells (all empty), so the error comes from Excel's own first pass over the cycle, not from stored values. Once `#VALUE!` enters the cycle, iteration cannot clear it. The ADR 0006 breaker reset clears it because it makes Excel calculate once with the loop broken, so iteration starts from numbers.

Values after the breaker reset, and cold for comparison:

| Cell | After reset | Cold |
|---|---|---|
| Schedules!J43 | 149.538075 | 149.538075 |
| Schedules!J44 | 0.0 | #VALUE! |
| Schedules!J45 | 831.796351 | #VALUE! |
| IS!J22 | 9982.338516 | #VALUE! |
| CF!J18 | -2695.231399 | #VALUE! |
| CF!J27 | -207.000000 | #VALUE! |
| BS!J9 | 20000.000000 | #VALUE! |
| Checks!C21 (MasterCheck) | 0.0 | #VALUE! |

Excel's `CalculationState` read 2 (pending) after `CalculateFull` in both states. The workbook was closed without saving each time, and `git status` shows it unchanged.
