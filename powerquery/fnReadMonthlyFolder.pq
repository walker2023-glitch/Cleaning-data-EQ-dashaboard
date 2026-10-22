// Example only. Load as fnReadMonthlyFolder in a COPY of the PBIX.
// A direct, immutable snapshot/report folder, NEVER versions/ or all review_packets/.
// ReviewCandidates defaults false. Current app outputs require explicit true in a
// separate review model; this switch is not an approval or a publishing mechanism.
(FolderPath as text, ReportKind as text, optional ReviewCandidates as nullable logical) as table =>
let
    Specs = [
        repairs = {{"LegacyRowNumber", "integer"}, {"CompletedDate", "date"}, {"EquipmentName", "text"}, {"EquipmentId", "text"}, {"Location", "text"}, {"ServiceVendor", "text"}, {"RepairCount", "integer"}, {"RepairPersonHours", "decimal"}, {"PartsCost", "decimal"}, {"LaborCost", "decimal"}, {"EstimatedTotalCost", "decimal"}, {"LegacyPartsCost", "decimal"}, {"LegacyEstimatedTotalCost", "decimal"}, {"RawPartsCost", "text"}, {"RawTextbox16", "text"}, {"Description", "text"}, {"Details", "text"}, {"AccountName", "text"}, {"RawEquipmentId", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}},
        service_orders = {{"EquipmentId", "text"}, {"EquipmentName", "text"}, {"ScheduledDate", "date"}, {"CompletedDate", "date"}, {"Location", "text"}, {"Description", "text"}, {"Status", "text"}, {"RawStatus", "text"}, {"EstimatedPrice", "decimal"}, {"RawDescription", "text"}, {"SourceMaintenanceTag", "text"}, {"AccountName", "text"}, {"SourceVendorName", "text"}, {"RawCost", "text"}, {"RawEquipmentId", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}},
        tma_work_orders = {{"WorkOrderId", "text"}, {"RequestDate", "date"}, {"Requestor", "text"}, {"Request", "text"}, {"AssignedTo", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}}
    ],
    Spec = if Record.HasFields(Specs, ReportKind) then Record.Field(Specs, ReportKind) else error "Unsupported report type",
    Names = List.Transform(Spec, each _{0}),
    Review = if ReviewCandidates = null then false else ReviewCandidates,
    Status = if Review then "CandidateUnverified" else "Approved",
    // Folder.Contents is intentionally nonrecursive; skip directories and temporary files.
    Files = Table.SelectRows(Folder.Contents(FolderPath), each [Extension] <> null and Text.Lower([Extension]) = ".csv"
        and not Text.StartsWith([Name], ".") and not Text.StartsWith([Name], "~")
        and [Attributes]?[Directory]? <> true),
    Parse = (Content as binary) as table =>
        let
            Csv = Csv.Document(Content, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv, ExtraValues=ExtraValues.Error]),
            Header = if Table.RowCount(Csv) > 1 then Record.FieldValues(Csv{0}) else error "Empty CSV",
            Exact = if Header = Names then Table.PromoteHeaders(Csv, [PromoteAllScalars=true]) else error "Incompatible schema",
            // Keep every identifier as text; dates and decimals use explicit invariant formats.
            Converters = List.Transform(Spec, (Col) => {Col{0}, (Value) =>
                if Col{1} = "text" then (if Value = null then "" else Text.From(Value))
                else if Value = null or Value = "" then null
                else if Col{1} = "date" then
                    let D = Date.FromText(Value, [Format="yyyy-MM-dd", Culture="en-US"])
                    in if Date.ToText(D, [Format="yyyy-MM-dd", Culture="en-US"]) = Value then D else error "Invalid ISO date"
                else let N = Number.FromText(Value, "en-US")
                    in if Number.IsNaN(N) or N = #infinity or N = -#infinity then error "Invalid number"
                    else if Col{1} = "integer" and Number.RoundTowardZero(N) <> N then error "Invalid integer" else N,
                if Col{1} = "date" then type nullable date else if Col{1} = "integer" then Int64.Type
                else if Col{1} = "decimal" then type nullable number else type text}),
            Typed = Table.TransformColumns(Exact, Converters, null, MissingField.Error),
            Periods = List.Distinct(Typed[ReportMonth]),
            Period = if List.Count(Periods) = 1 then Periods{0} else error "More than one month in a CSV",
            PeriodDate = try Date.FromText(Period & "-01", [Format="yyyy-MM-dd", Culture="en-US"]) otherwise error "Invalid report month",
            ValidPeriod = Date.ToText(PeriodDate, [Format="yyyy-MM", Culture="en-US"]) = Period,
            Checked = if Table.RowCount(Table.SelectRowsWithErrors(Typed)) = 0
                and ValidPeriod and Table.RowCount(Typed) > 0
                and List.AllTrue(List.Transform(Typed[ReportType], each _ = ReportKind))
                and List.AllTrue(List.Transform(Typed[ExportVersion], each _ = "powerbi-v1"))
                and List.AllTrue(List.Transform(Typed[SchemaVersion], each _ = "1"))
                and List.AllTrue(List.Transform(Typed[ValidationStatus], each _ = Status))
                and List.Count(List.Distinct(Typed[RecordId])) = Table.RowCount(Typed)
                then Typed else error "Metadata, status or record identity rejected"
        in Checked,
    Tables = List.Transform(Files[Content], each Parse(_)),
    Months = List.Transform(Tables, each _{0}[ReportMonth]),
    Combined = if List.Count(Tables) = 0 then error "No monthly CSV files"
        else if List.Count(List.Distinct(Months)) <> List.Count(Months) then error "Duplicate reporting month"
        else Table.Combine(Tables),
    CheckedRecords = if List.Count(List.Distinct(Combined[RecordId])) = Table.RowCount(Combined)
        then Combined else error "Duplicate record identity"
in
    CheckedRecords
