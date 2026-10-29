// Comparison only. Aggregate repair facts BEFORE joining the monthly summary.
// Requires PilotMonths and the four Pilot* tables; never edits existing DAX.
let
    KnownSum = (Values as list) as nullable number =>
        let Known = List.RemoveNulls(Values) in if List.Count(Known) = 0 then null else List.Sum(Known),
    Repairs = Table.Group(PilotRepairsV2, {"ReportMonth"}, {
        {"RepairRecords", each Table.RowCount(_), Int64.Type},
        {"KnownIndividualTotalCost", each KnownSum([ReportedTotalCost]), type nullable number},
        {"MissingRepairCosts", each List.Count([ReportedTotalCost])-List.NonNullCount([ReportedTotalCost]), Int64.Type},
        {"RepairPersonHours", each KnownSum([RepairPersonHours]), type nullable number},
        {"EstimatedLaborCost", each KnownSum([EstimatedLaborCost]), type nullable number}}),
    SummaryFields = {"ReportedLaborCost", "ReportedPartsCost", "ReportedTotalCost", "ReportedRepairCount",
        "SourceRecordCount", "RetainedRepairCount", "KnownRepairTotalCost", "UnavailableRepairCostCount",
        "RepairTotalDifference", "SummaryComponentsDifference", "ReconciliationStatus"},
    Joined = Table.NestedJoin(Repairs, {"ReportMonth"}, PilotRepairFinancialSummary, {"ReportMonth"}, "Monthly", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "Monthly", SummaryFields, SummaryFields),
    Services = Table.Group(PilotServiceOrders, {"ReportMonth"}, {{"ServiceOrderRecords", each Table.RowCount(_), Int64.Type}}),
    Tma = Table.Group(PilotTmaWorkOrders, {"ReportMonth"}, {{"TmaWorkOrderRecords", each Table.RowCount(_), Int64.Type}}),
    WithServices = Table.ExpandTableColumn(Table.NestedJoin(Expanded, {"ReportMonth"}, Services, {"ReportMonth"}, "Services", JoinKind.LeftOuter), "Services", {"ServiceOrderRecords"}),
    WithTma = Table.ExpandTableColumn(Table.NestedJoin(WithServices, {"ReportMonth"}, Tma, {"ReportMonth"}, "Tma", JoinKind.LeftOuter), "Tma", {"TmaWorkOrderRecords"}),
    Difference = Table.AddColumn(WithTma, "CalculatedRepairTotalDifference", each
        if [MissingRepairCosts] = 0 and [SourceRecordCount] = [RepairRecords] and [ReportedTotalCost] <> null
        then [KnownIndividualTotalCost] - [ReportedTotalCost] else null, type nullable number),
    Components = Table.AddColumn(Difference, "CalculatedComponentsDifference", each
        if List.NonNullCount({[ReportedLaborCost], [ReportedPartsCost], [ReportedTotalCost]}) = 3
        then [ReportedLaborCost] + [ReportedPartsCost] - [ReportedTotalCost] else null, type nullable number),
    Status = Table.AddColumn(Components, "ReviewStatus", each
        if [ServiceOrderRecords] = null or [TmaWorkOrderRecords] = null
            or [MissingRepairCosts] <> 0 or [SourceRecordCount] <> [RepairRecords]
            or [CalculatedRepairTotalDifference] = null or [CalculatedComponentsDifference] = null
        then "Incomplete - review required"
        else if [ReportedRepairCount] <> [RepairRecords] or [RetainedRepairCount] <> [RepairRecords]
            or [UnavailableRepairCostCount] <> [MissingRepairCosts]
            or [KnownRepairTotalCost] <> [KnownIndividualTotalCost]
            or [RepairTotalDifference] <> [CalculatedRepairTotalDifference]
            or [SummaryComponentsDifference] <> [CalculatedComponentsDifference]
            or [CalculatedRepairTotalDifference] <> 0 or [CalculatedComponentsDifference] <> 0
            or [ReconciliationStatus] <> "arithmetic_match"
        then "Difference - review required" else "Arithmetic match - candidate only", type text),
    Complete = if Table.RowCount(Status) = List.Count(PilotMonths)
        and List.Sort(Status[ReportMonth]) = List.Sort(PilotMonths)
        then Status else error "Pilot query periods differ; check PilotMonths and the exact snapshot",
    Candidate = Table.AddColumn(Complete, "ValidationStatus", each "CandidateUnverified", type text)
in Candidate
