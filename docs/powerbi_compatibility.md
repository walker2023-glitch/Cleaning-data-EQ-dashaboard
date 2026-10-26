# Existing model compatibility review

> **Superseded for current repair finances:** recommended output now uses repair
> schema v2. See [repair_financial_v2.md](repair_financial_v2.md) for confirmed
> total-cost mapping, separate monthly summaries, evidence limits and migration.
> Schema-v1 details below remain compatibility/history documentation; source-reported
> totals must not be interpreted as parts or have estimated labor added to them.


The actual PBIX, column inventory and DAX definitions are not present. The table
concepts `Compuclean list` and `Service_Orders` come from design.md; the TMA table
name is unknown. The following mappings target **known legacy cleaner columns**
as review proposals. They do not assert the existing model's exact schema.

| Normalized repair field | Known legacy candidate column | Review requirement |
|---|---|---|
| LegacyRowNumber | # | Restarts every file; never a unique relationship key |
| CompletedDate | Completed Date | ISO date to date; confirm calendar relationship |
| EquipmentName / EquipmentId | Equipment Name / Equipment ID | Keep ID text; no zero-padding guesses |
| Location / ServiceVendor | Location / Service Vendor | Preserve Building_Dim key policy; no invented joins |
| RepairCount | # of Repairs | SUM vs COUNTROWS depends on existing measure grain |
| RepairPersonHours | Repair Person-Hrs | Numeric hours, not time-of-day or text |
| PartsCost | Parts Cost $ | Nullable normalized view; Textbox38 meaning unverified |
| LaborCost | Total Labor $ | Existing estimate, not proven actual labor |
| EstimatedTotalCost | Est. Total $ | Nullable when parts unavailable; unverified semantics |
| LegacyPartsCost / LegacyEstimatedTotalCost | Same legacy financial columns | Comparison alternative only; never sum both views |

| Normalized service field | Known legacy candidate column | Review requirement |
|---|---|---|
| EquipmentId / EquipmentName | Equipment Id / Equipment Name | Exact spelling/case differs from repair header; keep ID text |
| ScheduledDate / CompletedDate | Sched. Date / Completed Date | Existing inclusion is scheduled OR completed month; calendar basis needs approval |
| Location / Description / Status | Location / Description / Status | Description follows existing exclusions/suffix stripping |
| EstimatedPrice | Estimated Price | Missing/nonpositive remains null under current convention |

| Normalized TMA field | Known legacy candidate column | Review requirement |
|---|---|---|
| WorkOrderId | Work Order # | Text; not an equipment ID or verified cross-system event key |
| RequestDate | Request Date | ISO date; existing candidate was MM/DD/YYYY |
| Requestor / Request / AssignedTo | Requestor / Request / Assigned To | Optional assignee remains blank; protect personal data |

All three add ReportMonth and provenance. RecordId identifies a retained occurrence
in a particular source revision, not an established model key. Do not join TMA
work-order IDs to equipment IDs. Maintenance tags are source metadata, not an
approved PM/repair classification. Repeated service/repair totals are metadata,
not extra fact rows. Financial columns and SourceMaintenanceTag must not become
production measures/classification without business review.

Before source migration, make a private inventory with columns: existing table,
existing column/type, proposed normalized column/type, semantic/date grain,
relationship endpoints/cardinality/filter direction, impacted DAX/calculated
columns/sort/RLS, null behavior, decision, reviewer, evidence. Include disconnected
tables, calculation groups and measures that use ALL/REMOVEFILTERS/USERELATIONSHIP.
Confirm cross-month service events and corrected-month selection explicitly.

For pilot-only controls, add measures on new pilot tables if useful, for example:

```dax
Pilot Repair Count = SUM(PilotRepairs[RepairCount])
Pilot Repair Hours = SUM(PilotRepairs[RepairPersonHours])
Pilot Service Rows = COUNTROWS(PilotServiceOrders)
Pilot TMA Rows = COUNTROWS(PilotTmaWorkOrders)
```

These names/formulas are examples for the new tables, not replacements for existing
DAX. A simple SUM can hide null inputs: inspect PilotControlTotals.missing_values
as well. A measure's date filter must use the intended reporting month, not an
unrelated existing calendar relationship. Compare monthly and full selected-period
counts, distinct IDs, missing IDs, dates, null/zero amounts, costs/hours and
Building_Dim/calendar joins. Check every page's slicers, maps, tooltips and totals.

Keep the current tables intact for this pilot. Any later approved migration should
change source/query steps on the existing tables after an exact contract is agreed;
deleting and recreating them can break identities/relationships/DAX. Keep rollback
PBIX and snapshot. Do not publish even the backup copy without separate approval.
