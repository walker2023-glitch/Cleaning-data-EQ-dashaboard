// OPTIONAL BACKUP-PBIX VIEW. Existing pilot text fields preserve empty strings.
// CSV missing values are empty fields, never the literal text "null".
// Keep the original pilot query; use this separate view if DAX needs true null.
let
    Source = PilotTmaWorkOrders,
    Checked = if Table.HasColumns(Source, {"AssignedTo"}) then Source else error "Missing AssignedTo",
    NullableAssignments = Table.TransformColumns(Checked, {{"AssignedTo", each if _ = null or _ = "" then null else _, type nullable text}})
in
    NullableAssignments
