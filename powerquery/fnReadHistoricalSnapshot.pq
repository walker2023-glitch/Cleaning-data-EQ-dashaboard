// BACKUP PBIX ONLY. Run Python --verify-snapshot before import. No cryptographic validation in M.
(SnapshotFolder as text, ReportKind as text, optional AllowUnapprovedTest as nullable logical) as table =>
let
    Specs = [
        repairs = {{"LegacyRowNumber", "integer"}, {"CompletedDate", "date"}, {"EquipmentName", "text"}, {"EquipmentId", "text"}, {"Location", "text"}, {"ServiceVendor", "text"}, {"RepairCount", "integer"}, {"RepairPersonHours", "decimal"}, {"ReportedTotalCost", "decimal"}, {"ReportedTotalCostStatus", "text"}, {"EstimatedLaborCost", "decimal"}, {"LegacyPartsCost", "decimal"}, {"LegacyLaborCost", "decimal"}, {"LegacyEstimatedTotalCost", "decimal"}, {"RawTextbox38", "text"}, {"RawTextbox16", "text"}, {"Description", "text"}, {"Details", "text"}, {"AccountName", "text"}, {"RawEquipmentId", "text"}, {"FinancialSummarySHA256", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}, {"ReportingMonth", "text"}, {"CandidateRevisionId", "text"}, {"CandidateOutputSHA256", "text"}, {"CandidateCleanerVersion", "text"}},
        service_orders = {{"EquipmentId", "text"}, {"EquipmentName", "text"}, {"ScheduledDate", "date"}, {"CompletedDate", "date"}, {"Location", "text"}, {"Description", "text"}, {"Status", "text"}, {"RawStatus", "text"}, {"EstimatedPrice", "decimal"}, {"RawDescription", "text"}, {"SourceMaintenanceTag", "text"}, {"AccountName", "text"}, {"SourceVendorName", "text"}, {"RawCost", "text"}, {"RawEquipmentId", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}, {"ReportingMonth", "text"}, {"CandidateRevisionId", "text"}, {"CandidateOutputSHA256", "text"}, {"CandidateCleanerVersion", "text"}},
        tma_work_orders = {{"WorkOrderId", "text"}, {"RequestDate", "date"}, {"Requestor", "text"}, {"Request", "text"}, {"AssignedTo", "text"}, {"RecordId", "text"}, {"ReportMonth", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"SourceRecordNumber", "integer"}, {"CandidateRecordNumber", "integer"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}, {"ReportingMonth", "text"}, {"CandidateRevisionId", "text"}, {"CandidateOutputSHA256", "text"}, {"CandidateCleanerVersion", "text"}},
        repair_financial_summary = {{"ReportMonth", "text"}, {"ReportedLaborCost", "decimal"}, {"ReportedPartsCost", "decimal"}, {"ReportedTotalCost", "decimal"}, {"ReportedRepairCount", "integer"}, {"SourceRecordCount", "integer"}, {"RetainedRepairCount", "integer"}, {"KnownRepairTotalCost", "decimal"}, {"UnavailableRepairCostCount", "integer"}, {"RepairTotalDifference", "decimal"}, {"SummaryComponentsDifference", "decimal"}, {"ReconciliationStatus", "text"}, {"SourceSystem", "text"}, {"ReportType", "text"}, {"SourceFileName", "text"}, {"SourceFileSHA256", "text"}, {"LegacyCandidateSHA256", "text"}, {"CleanerVersion", "text"}, {"ExportVersion", "text"}, {"SchemaVersion", "text"}, {"ValidationStatus", "text"}, {"EstimatedLaborCostSum", "decimal"}, {"EstimatedLaborCostMissingCount", "integer"}, {"LegacyPartsCostSum", "decimal"}, {"LegacyPartsCostMissingCount", "integer"}, {"LegacyLaborCostSum", "decimal"}, {"LegacyLaborCostMissingCount", "integer"}, {"LegacyEstimatedTotalCostSum", "decimal"}, {"LegacyEstimatedTotalCostMissingCount", "integer"}, {"ReportingMonth", "text"}, {"CandidateRevisionId", "text"}, {"CandidateOutputSHA256", "text"}, {"CandidateCleanerVersion", "text"}}
    ],
    Manifest = Json.Document(File.Contents(SnapshotFolder & "/snapshot_manifest.json")),
    Checked = if AllowUnapprovedTest = true and Manifest[snapshot_schema] = "historical-powerbi-v1"
        and Manifest[status] = "CandidateUnverified" and Manifest[approval_status] = "NotApproved"
        and Manifest[production_ready] = false and Manifest[complete] = true
        then Manifest else error "Explicit unapproved backup test and complete snapshot required",
    Spec = Record.Field(Specs, ReportKind),
    Names = List.Transform(Spec, each _{0}),
    Matches = List.Select(Checked[datasets], each _[report_type] = ReportKind),
    Entry = if List.Count(Matches) = 1 then Matches{0} else error "Missing or duplicate dataset",
    Files = [repairs="Repairs_History.csv", service_orders="ServiceOrders_History.csv",
        tma_work_orders="TMAWorkOrders_History.csv", repair_financial_summary="RepairFinancialSummaries.csv"],
    Name = if Entry[file] = Record.Field(Files, ReportKind) and Entry[columns] = Names
        then Entry[file] else error "Incompatible dataset contract",
    Csv = Csv.Document(File.Contents(SnapshotFolder & "/" & Name),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv, ExtraValues=ExtraValues.Error]),
    Header = if Table.RowCount(Csv) > 1 then Record.FieldValues(Csv{0}) else error "Empty dataset",
    Exact = if Header = Names then Table.PromoteHeaders(Csv, [PromoteAllScalars=true]) else error "Incompatible headers",
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
    Typed = Table.TransformColumns(Exact, Converters),
    SourceKind = if ReportKind = "repair_financial_summary" then "repairs" else ReportKind,
    Selections = List.Select(Checked[selections], each _[report_type] = SourceKind),
    Months = List.Sort(List.Distinct(List.Transform(Selections, each _[month]))),
    Complete = List.Count(Selections) = List.Count(Months) and List.AllTrue(List.Transform(Selections, each _[status] = "ready")),
    Invalid = Table.SelectRows(Typed, (R) =>
        let S = List.Select(Selections, each _[month] = R[ReportingMonth])
        in if List.Count(S) <> 1 then true else R[ReportMonth] <> R[ReportingMonth]
            or R[CandidateRevisionId] <> S{0}[revision] or R[CandidateOutputSHA256] <> S{0}[output_sha256]
            or R[CandidateCleanerVersion] <> S{0}[cleaner_version] or R[SourceFileSHA256] <> S{0}[source_sha256]
            or R[ValidationStatus] <> "CandidateUnverified"),
    Coverage = List.Sort(List.Distinct(Typed[ReportingMonth])) = Months,
    Result = if Complete and Coverage and Table.RowCount(Invalid) = 0 and Table.RowCount(Typed) = Entry[rows]
        then Typed else error "Dataset count, coverage or revision binding mismatch"
in
    Result
