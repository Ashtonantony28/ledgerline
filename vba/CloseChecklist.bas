Attribute VB_Name = "CloseChecklist"
' Ledgerline workbook 05: stamp a close-checklist task as signed off.
' Select a row on the Checklist sheet and run SignOff. The macro refuses while MasterCheck <> 0, so a task
' cannot be signed off on a close that does not tie. Needs desktop Excel (verified at M10); the workbook
' itself calculates without macros.
Option Explicit

Private Const SIGN_COL As String = "D"   ' "Signed off by"
Private Const DATE_COL As String = "E"   ' "Signed off at"
Private Const FIRST_ROW As Long = 5

Public Sub SignOff()
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets("Checklist")
    If ActiveSheet.Name <> ws.Name Then
        MsgBox "Select a task on the Checklist sheet first.", vbExclamation: Exit Sub
    End If
    r = ActiveCell.Row
    If r < FIRST_ROW Or Len(ws.Cells(r, 2).Value) = 0 Then
        MsgBox "Select a row that holds a task.", vbExclamation: Exit Sub
    End If
    If ThisWorkbook.Names("MasterCheck").RefersToRange.Value <> 0 Then
        MsgBox "The close does not tie (see Checks). Fix it before signing off.", vbCritical: Exit Sub
    End If
    ws.Range(SIGN_COL & r).Value = Application.UserName
    ws.Range(DATE_COL & r).Value = Now
    ws.Range(DATE_COL & r).NumberFormat = "yyyy-mm-dd hh:mm"
End Sub

Public Sub ClearSignOffs()
    Dim ws As Worksheet, last As Long
    Set ws = ThisWorkbook.Worksheets("Checklist")
    last = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row
    If last >= FIRST_ROW Then ws.Range(SIGN_COL & FIRST_ROW & ":" & DATE_COL & last).ClearContents
End Sub
