Attribute VB_Name = "ReconPack"
' Ledgerline workbook 05: highlight reconciling items and export the reconciliation pack to PDF.
' Needs desktop Excel (verified at M10).
Option Explicit

Private Const STATUS_COL As Long = 7     ' column G: "Reconciled" / "Explained (J6)" / "OPEN"

Public Sub HighlightBreaks()
    ' Shade every reconciliation whose status formula says OPEN; the tolerance lives in Inputs (no literal here).
    Dim ws As Worksheet, r As Long, last As Long
    Set ws = ThisWorkbook.Worksheets("Recs")
    last = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    For r = 1 To last
        If ws.Cells(r, STATUS_COL).Value = "OPEN" Then
            ws.Range(ws.Cells(r, 1), ws.Cells(r, STATUS_COL)).Interior.Color = RGB(255, 199, 206)
        ElseIf ws.Cells(r, STATUS_COL).HasFormula Then
            ws.Range(ws.Cells(r, 1), ws.Cells(r, STATUS_COL)).Interior.ColorIndex = xlNone
        End If
    Next r
End Sub

Public Sub ExportPack()
    Dim path As String
    HighlightBreaks
    path = ThisWorkbook.Path & Application.PathSeparator & "Recon_Pack_" & Format(Date, "yyyy-mm-dd") & ".pdf"
    ThisWorkbook.Worksheets(Array("Recs", "Checks", "Checklist")).Select
    ActiveSheet.ExportAsFixedFormat Type:=xlTypePDF, Filename:=path, Quality:=xlQualityStandard, OpenAfterPublish:=False
    ThisWorkbook.Worksheets("Recs").Select
    MsgBox "Saved " & path, vbInformation
End Sub
