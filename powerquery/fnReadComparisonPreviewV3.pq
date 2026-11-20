// DEVELOPMENT COMPARISON V3 ONLY. IDs/Building already derived; do not reapply legacy transforms. Run Python --verify first; M does not verify hashes.
// Existing canonical helpers and production PBIX queries remain unchanged.
(ComparisonFolder as text, ReportKind as text, optional AllowDevelopmentComparison as nullable logical) as table =>
let
    Specs = [
        repairs = {{"ReportMonth", "text"}, {"CompletedDate", "date"}, {"EquipmentName", "text"}, {"EquipmentId", "text"}, {"Location", "text"}, {"Building", "text"}, {"ServiceVendor", "text"}, {"RepairCount", "integer"}, {"RepairPersonHours", "decimal"}, {"ReportedTotalCost", "decimal"}, {"ReportedTotalCostStatus", "text"}, {"EstimatedLaborCost", "decimal"}, {"LegacyPartsCost", "decimal"}, {"LegacyLaborCost", "decimal"}, {"LegacyEstimatedTotalCost", "decimal"}, {"Description", "text"}, {"Details", "text"}, {"AccountName", "text"}, {"RawEquipmentId", "text"}, {"ObservedEquipmentName", "text"}, {"EquipmentType", "text"}, {"MaintenanceType", "text"}},
        service_orders = {{"ReportMonth", "text"}, {"EquipmentId", "text"}, {"EquipmentName", "text"}, {"ScheduledDate", "date"}, {"CompletedDate", "date"}, {"Location", "text"}, {"Building", "text"}, {"Description", "text"}, {"Status", "text"}, {"RawStatus", "text"}, {"EstimatedPrice", "decimal"}, {"RawDescription", "text"}, {"SourceMaintenanceTag", "text"}, {"AccountName", "text"}, {"SourceVendorName", "text"}, {"RawCost", "text"}, {"RawEquipmentId", "text"}, {"ObservedEquipmentName", "text"}, {"EquipmentType", "text"}, {"MaintenanceType", "text"}},
        tma_work_orders = {{"ReportMonth", "text"}, {"WorkOrderId", "text"}, {"RequestDate", "date"}, {"Requestor", "text"}, {"Request", "text"}, {"AssignedTo", "text"}},
        repair_financial_summary = {{"ReportMonth", "text"}, {"ReportedLaborCost", "decimal"}, {"ReportedPartsCost", "decimal"}, {"ReportedTotalCost", "decimal"}, {"ReportedRepairCount", "integer"}, {"SourceRecordCount", "integer"}, {"RetainedRepairCount", "integer"}, {"KnownRepairTotalCost", "decimal"}, {"UnavailableRepairCostCount", "integer"}, {"RepairTotalDifference", "decimal"}, {"SummaryComponentsDifference", "decimal"}, {"ReconciliationStatus", "text"}, {"EstimatedLaborCostSum", "decimal"}, {"EstimatedLaborCostMissingCount", "integer"}, {"LegacyPartsCostSum", "decimal"}, {"LegacyPartsCostMissingCount", "integer"}, {"LegacyLaborCostSum", "decimal"}, {"LegacyLaborCostMissingCount", "integer"}, {"LegacyEstimatedTotalCostSum", "decimal"}, {"LegacyEstimatedTotalCostMissingCount", "integer"}},
        equipment = {{"EquipmentId", "text"}, {"EquipmentName", "text"}, {"EquipmentType", "text"}, {"FirstObservedMonth", "text"}, {"LastObservedMonth", "text"}, {"ObservationCount", "integer"}, {"NameConflict", "boolean"}}
    ],
    Manifest = Json.Document(File.Contents(ComparisonFolder & "/comparison_manifest.json")),
    Checked = if AllowDevelopmentComparison = true and Manifest[export_schema] = "comparison-preview-v3"
        and Manifest[purpose] = "DevelopmentComparison" and Manifest[status] = "CandidateUnverified"
        and Manifest[approval_status] = "NotApproved" and Manifest[production_ready] = false
        then Manifest else error "Explicit development comparison required",
    Spec = Record.Field(Specs, ReportKind),
    Names = List.Transform(Spec, each _{0}),
    Files = [repairs="Repairs_History.csv", service_orders="ServiceOrders_History.csv",
        tma_work_orders="TMAWorkOrders_History.csv", repair_financial_summary="RepairFinancialSummaries.csv", equipment="Equipment_History.csv"],
    Matches = List.Select(Checked[datasets], each _[report_type] = ReportKind),
    Entry = if List.Count(Matches) = 1 then Matches{0} else error "Missing or duplicate comparison dataset",
    Name = if Entry[file] = Record.Field(Files, ReportKind)
        and List.Transform(Entry[columns], each _[name]) = Names
        and List.Transform(Entry[columns], each _[type]) = List.Transform(Spec, each _{1})
        then Entry[file] else error "Incompatible comparison contract",
    Csv = Csv.Document(File.Contents(ComparisonFolder & "/" & Name),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv, ExtraValues=ExtraValues.Error]),
    Header = if Table.RowCount(Csv) >= 1 then Record.FieldValues(Csv{0}) else error "Empty comparison dataset",
    Exact = if Header = Names then Table.PromoteHeaders(Csv, [PromoteAllScalars=true]) else error "Incompatible comparison headers",
    Converters = List.Transform(Spec, (Col) => {Col{0}, (Value) =>
        if Col{1} = "text" then (if Value = null then "" else Text.From(Value))
        else if Value = null or Value = "" then null
        else if Col{1} = "boolean" then
            if Value = "true" then true else if Value = "false" then false else error "Invalid boolean"
        else if Col{1} = "date" then
            let D = Date.FromText(Value, [Format="yyyy-MM-dd", Culture="en-US"])
            in if Date.ToText(D, [Format="yyyy-MM-dd", Culture="en-US"]) = Value then D else error "Invalid ISO date"
        else let N = Number.FromText(Value, "en-US")
            in if Number.IsNaN(N) or N = #infinity or N = -#infinity then error "Invalid number"
            else if Col{1} = "integer" and Number.RoundTowardZero(N) <> N then error "Invalid integer" else N,
        if Col{1} = "boolean" then type logical else if Col{1} = "date" then type nullable date else if Col{1} = "integer" then Int64.Type
        else if Col{1} = "decimal" then type nullable number else type text}),
    Typed = Table.TransformColumns(Exact, Converters),
    Months = Record.FieldNames(Entry[rows_by_month]),
    MonthColumn = if ReportKind = "equipment" then "FirstObservedMonth" else "ReportMonth",
    Coverage = List.Sort(List.Distinct(Table.Column(Typed, MonthColumn))) = List.Sort(Months),
    Counts = List.AllTrue(List.Transform(Months, (Month) =>
        Table.RowCount(Table.SelectRows(Typed, each Record.Field(_, MonthColumn) = Month)) = Record.Field(Entry[rows_by_month], Month))),
    Result = if Coverage and Counts and Table.RowCount(Typed) = Entry[rows]
        then Typed else error "Comparison row or monthly counts differ"
in
    Result
