# Mutation test (workbook 01)

Mutants: 40, equivalent (no observable change): 2, caught: 38/38 = 100.0%

| kind | where | caught by |
|---|---|---|
| hardcode | BS!R12 | audit |
| wrongrow | CF!L10 | audit+checks+reference |
| wholesign | IS!row 11 | reference |
| wholelag | IS!row 18 | reference |
| input | Scenarios!N18 | reference |
| hardcode | Drivers!L27 | audit |
| wrongrow | Schedules!R45 | audit+reference |
| wholesign | Schedules!row 50 | checks+reference |
| wholelag | BS!row 20 | checks+reference |
| input | Scenarios!S66 | reference |
| hardcode | CF!L20 | audit |
| wrongrow | BS!M15 | audit+checks+reference |
| wholesign | IS!row 15 | equivalent |
| wholelag | Schedules!row 43 | audit+reference |
| input | Scenarios!Q50 | reference |
| hardcode | IS!Q17 | audit |
| wrongrow | IS!O24 | audit+reference |
| wholesign | CF!row 27 | checks+reference |
| wholelag | Schedules!row 27 | checks+reference |
| input | Scenarios!K58 | reference |
| hardcode | Schedules!K13 | audit |
| wrongrow | BS!O26 | audit+checks+reference |
| wholesign | CF!row 18 | reference |
| wholelag | IS!row 22 | checks+reference |
| input | Scenarios!L50 | reference |
| hardcode | Drivers!K16 | audit |
| wrongrow | IS!J22 | audit+checks+reference |
| wholesign | CF!row 20 | reference |
| wholelag | IS!row 11 | reference |
| input | Scenarios!O26 | reference |
| hardcode | IS!S14 | audit |
| wrongrow | IS!M9 | audit+reference |
| wholesign | CF!row 29 | equivalent |
| wholelag | BS!row 9 | checks+reference |
| input | Scenarios!Q22 | reference |
| hardcode | CF!P25 | audit |
| wrongrow | BS!P25 | audit+checks+reference |
| wholesign | Schedules!row 10 | reference |
| wholelag | Schedules!row 13 | reference |
| input | Scenarios!M30 | reference |
