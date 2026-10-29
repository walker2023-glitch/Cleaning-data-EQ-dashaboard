# Backup dashboard migration plan — manual review only

No PBIX, existing measure expressions, relationship inventory or Building_Dim keys
are present in the repository. This is a procedure and dependency checklist, not
a claim to have found or changed actual model measures. Keep production closed;
retain the original PBIX and selected source snapshot as rollback evidence.

1. In an authorized **local test copy**, record table identities/names, columns/types,
   existing M source/append/type steps, DAX measures/calculated columns/tables,
   calculation groups, date/calendar roles, Building_Dim keys, sort-by columns,
   RLS, relationship endpoints/cardinality/filter direction and page/slicer settings.
   A copy retains live connections: use a blank PBIX for a strictly offline trial,
   or isolate all existing live queries deliberately before any refresh.
2. Import the separate Pilot* queries following powerbi_real_data_readiness.md.
   Do not delete/recreate `Compuclean list`, `Service_Orders`, existing TMA tables,
   building dimensions or their measures. Keep pilot tables disconnected initially;
   disable automatic new-relationship detection and review every generated link.
3. Use Desktop's DAX/query views or an IT-approved model export to make a **private**
   dependency inventory. Search expressions and M steps for the exact column names
   below, legacy spaced headers and dependent measures. Include dependencies through
   other measures, calculated tables, field parameters, implicit visual sums and
   format strings; a simple text hit alone is not a complete dependency analysis.
4. Compare new controls against the current cached/authorized baseline by identical
   reporting periods and filter context. Check monthly and combined counts, missing
   values, text IDs, dates, repair hours and estimated labor separately from source
   financial totals. Review ALL/REMOVEFILTERS, inactive calendar relationships and
   USERELATIONSHIP usage: some measures intentionally ignore a month slicer.
5. Complete financial meaning decisions before proposing replacements. Review table:

| Old column/reference to locate | Meaning/problem | Proposed review action, never automatic |
|---|---|---|
| PartsCost / Parts Cost $ | Legacy repair mapping used a total-cost field as parts | Keep LegacyPartsCost only for comparison. Actual reported parts exist at month grain in the separate summary, not per repair/equipment |
| LaborCost / Total Labor $ | Existing hours × retained estimate rate | Compare with EstimatedLaborCost/LegacyLaborCost; monthly source ReportedLaborCost is a different measure/grain |
| EstimatedTotalCost / Est. Total $ | Legacy calculation adds estimated labor to the source amount | Retain LegacyEstimatedTotalCost for comparison. Review using ReportedTotalCost for source totals; never add the estimate again |
| RawPartsCost | Name incorrectly suggested parts | v2 preserves RawTextbox38/RawTextbox16 as raw evidence, not numeric measures |
| RepairPersonHours / Repair Person-Hrs | Existing numeric duration/default heuristics | Preserve current values and units for monthly repair-hour/capacity visuals; do not label estimated/default hours verified |
| EquipmentId / Equipment ID / Equipment Id | Text identity and relationship keys | Preserve literal zeros; verify dimension uniqueness and exact mappings before any join |
| CompletedDate / ScheduledDate / RequestDate / ReportMonth | Different event/reporting date roles | Preserve calendar behavior and service scheduled-OR-completed inclusion; cross-month policy still needs management decision |

6. Test every page's visuals, maps, tooltips, drill hierarchy, slicers, totals,
   building/calendar joins, relationship filter direction, row-level security and
   sort order in the backup. Hour and capacity measures must retain their existing
   interpretation and inputs; source money does not establish hours or capacity.
   Do not replace Workday/capacity assumptions with inventory counts by inference.
7. Monthly financial summary is one row/month. Do not merge its reported parts/labor
   onto every transaction or join it directly to EquipmentId. Decide month/date
   dimension roles with the model owner; avoid ambiguous active many-to-many or
   bidirectional paths. Current equipment location is not historical repair location.
8. Only after separate sign-off, propose source/query-step changes **on the existing
   table identities** with an exact approved column contract. Do not rename columns
   merely to satisfy old DAX whose meaning is wrong. Where per-equipment actual
   parts/labor are unavailable, explicitly mark the visual unavailable or defer it;
   do not allocate monthly amounts. Preserve a rollback PBIX and prior snapshot.
9. Record data/finance/model reviewer, tested measures/pages/filters, remaining
   differences and evidence. Test-workspace publication and production migration,
   refresh ownership/gateway credentials and authenticated approval are later,
   separately authorized actions. No automated measure replacement is included.
