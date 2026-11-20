// Ledgerline workbook 06: ingest the monthly GL export into a month-by-row table (Power Query M).
// In Excel: Data > Get Data > From Text/CSV is replaced by this query (Data > Queries > New > Blank, Advanced Editor).
// Point GLPath at fixtures/fpa/actuals.csv. The query pivots the long export (month, account, dimension, value)
// into one row per account/dimension and one column per month, the layout of the Actuals sheet, so a new month
// of actuals is a Refresh, not a paste. Needs desktop Excel (verified at M10); the committed workbook embeds the
// same values so it calculates without the query.
let
    GLPath = "actuals.csv",
    Source = Csv.Document(File.Contents(GLPath), [Delimiter = ",", Columns = 4, Encoding = 65001, QuoteStyle = QuoteStyle.None]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"month", Int64.Type}, {"account", type text}, {"dimension", type text}, {"value", type number}}),
    Keyed = Table.AddColumn(Typed, "line", each [account] & "_" & [dimension], type text),
    Slim = Table.SelectColumns(Keyed, {"line", "month", "value"}),
    MonthText = Table.TransformColumns(Slim, {{"month", each "M" & Text.PadStart(Text.From(_), 2, "0"), type text}}),
    Pivoted = Table.Pivot(MonthText, List.Sort(List.Distinct(MonthText[month])), "month", "value", List.Sum),
    // ingestion control: every product revenue line must tie to the GL control total each month
    Check = let
                Rev = Table.SelectRows(Typed, each [account] = "revenue"),
                Ctl = Table.SelectRows(Typed, each [account] = "gl_revenue"),
                Sums = Table.Group(Rev, {"month"}, {{"rev", each List.Sum([value]), type number}}),
                Joined = Table.Join(Sums, "month", Ctl, "month"),
                Breaks = Table.SelectRows(Joined, each Number.Abs([rev] - [value]) > 0.0005)
            in
                Table.RowCount(Breaks),
    Result = if Check = 0 then Pivoted else error Error.Record("GL tie-out", "Product revenue does not tie to the GL control total", Check)
in
    Result
