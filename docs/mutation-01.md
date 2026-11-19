# Mutation test (workbook 01)

Mutants: 40, equivalent (no observable change): 1, caught: 39/39 = 100.0%

| kind | where | caught by |
|---|---|---|
| hardcode | BS!R12 | audit |
| wrongrow | CF!L10 | audit+checks+reference |
| wholesign | IS!row 11 | reference |
| wholelag | IS!row 18 | reference |
| input | Scenarios!R22 | reference |
| hardcode | Schedules!R45 | audit |
| wrongrow | Schedules!P50 | audit+checks+reference |
| wholesign | BS!row 20 | checks+reference |
| wholelag | BS!row 16 | checks+reference |
| input | Scenarios!L38 | reference |
| hardcode | IS!J11 | audit |
| wrongrow | Drivers!P16 | audit+checks+reference |
| wholesign | CF!row 18 | reference |
| wholelag | Schedules!row 43 | audit+reference |
| input | Scenarios!L62 | reference |
| hardcode | BS!R12 | audit |
| wrongrow | CF!Q21 | audit+checks+reference |
| wholesign | Schedules!row 53 | checks+reference |
| wholelag | BS!row 27 | checks+reference |
| input | Scenarios!S54 | reference |
| hardcode | CF!R27 | audit |
| wrongrow | CF!Q10 | audit+checks+reference |
| wholesign | Schedules!row 27 | checks+reference |
| wholelag | Schedules!row 54 | audit+reference |
| input | Scenarios!S46 | reference |
| hardcode | CF!L18 | audit |
| wrongrow | CF!R19 | audit+reference |
| wholesign | IS!row 15 | equivalent |
| wholelag | IS!row 22 | checks+reference |
| input | Scenarios!R58 | reference |
| hardcode | BS!P32 | audit |
| wrongrow | IS!J22 | audit+checks+reference |
| wholesign | CF!row 20 | reference |
| wholelag | IS!row 11 | reference |
| input | Scenarios!L30 | reference |
| hardcode | IS!S14 | audit |
| wrongrow | Schedules!R41 | audit |
| wholesign | Schedules!row 19 | checks+reference |
| wholelag | CF!row 25 | checks+reference |
| input | Scenarios!S54 | reference |
