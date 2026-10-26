// Comparison-only aggregation; never replaces the cleaning engine or existing DAX.
// A known sum plus missing count is deliberate: partial sums are not complete totals.
(Rows as table, ReportKind as text) as table =>
let
    Specs = [
        repairs = {{"rows", null}, {"repair_count", "RepairCount"}, {"hours", "RepairPersonHours"},
            {"reported_total_cost", "ReportedTotalCost"}, {"estimated_labor_cost", "EstimatedLaborCost"},
            {"legacy_parts_cost", "LegacyPartsCost"}, {"legacy_labor_cost", "LegacyLaborCost"},
            {"legacy_estimated_total", "LegacyEstimatedTotalCost"}},
        service_orders = {{"rows", null}, {"service_price", "EstimatedPrice"}},
        tma_work_orders = {{"rows", null}}
    ],
    Spec = Record.Field(Specs, ReportKind),
    Groups = Table.Group(Rows, {"ReportMonth"}, {{"Controls", (Monthly) =>
        Table.FromRecords(List.Transform(Spec, (Metric) =>
            let Values = if Metric{1} = null then List.Repeat({1}, Table.RowCount(Monthly))
                else Table.Column(Monthly, Metric{1}),
                Known = List.RemoveNulls(Values)
            in [report_type=ReportKind, period=Monthly{0}[ReportMonth], metric=Metric{0},
                cleaned_known_sum=if List.Count(Known) = 0 then null else List.Sum(Known),
                missing_values=List.Count(Values)-List.Count(Known), validation_status="CandidateUnverified"])), type table}}),
    Combined = Table.Combine(Groups[Controls]),
    Typed = Table.TransformColumnTypes(Combined, {{"report_type", type text}, {"period", type text},
        {"metric", type text}, {"cleaned_known_sum", type nullable number},
        {"missing_values", Int64.Type}, {"validation_status", type text}})
in Typed
