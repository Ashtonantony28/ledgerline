# Mutation test (workbook 05)

Mutants: 40, equivalent (no observable change): 6, caught: 34/34 = 100.0%

| kind | where | caught by |
|---|---|---|
| hardcode | Consol!G42 | audit |
| wrongrow | TB_Adj!F22 | checks+reference |
| sign | Recs!F7 | checks+reference |
| input | TB_Unadj!F7 | checks+reference |
| hardcode | Recs!C8 | audit |
| wrongrow | Schedules!D7 | reference |
| sign | Statements!B18 | equivalent |
| input | Inputs!C9 | reference |
| hardcode | Schedules!C16 | audit |
| wrongrow | Journals!D20 | checks+reference |
| sign | Statements!B18 | equivalent |
| input | Inputs!C6 | reference |
| hardcode | Recs!D7 | equivalent |
| wrongrow | Elims!C19 | checks+reference |
| sign | Recs!F7 | checks+reference |
| input | Opening!E11 | checks+reference |
| hardcode | TB_Adj!C10 | audit |
| wrongrow | Translation!F21 | equivalent |
| sign | Recs!F20 | checks+reference |
| input | Inputs!E36 | reference |
| hardcode | Schedules!F16 | audit |
| wrongrow | Translation!B27 | equivalent |
| sign | Consol!I37 | checks+reference |
| input | Opening!D17 | checks+reference |
| hardcode | Consol!I17 | audit |
| wrongrow | Translation!F39 | equivalent |
| sign | Translation!F46 | checks+reference |
| input | Opening!E11 | checks+reference |
| hardcode | Consol!G34 | audit |
| wrongrow | CashFlow!H12 | checks+reference |
| sign | Recs!F15 | checks+reference |
| input | Inputs!C50 | checks+reference |
| hardcode | Consol!F12 | audit |
| wrongrow | CashFlow!F15 | checks+reference |
| sign | Recs!F18 | checks+reference |
| input | TB_Unadj!F24 | checks+reference |
| hardcode | Consol!H29 | audit |
| wrongrow | CashFlow!H20 | checks+reference |
| sign | Elims!C36 | reference |
| input | Opening!E21 | checks+reference |
