# Historical dataset CSV columns — historical-powerbi-v1

UTF-8; ordered columns. Empty numeric/date values are null. Text identifiers stay text.
Repairs remain financial schema 2; services/TMA remain schema 1.

## Repairs_History.csv

| Column | Type |
|---|---|
| LegacyRowNumber | integer |
| CompletedDate | date |
| EquipmentName | text |
| EquipmentId | text |
| Location | text |
| ServiceVendor | text |
| RepairCount | integer |
| RepairPersonHours | decimal |
| ReportedTotalCost | decimal |
| ReportedTotalCostStatus | text |
| EstimatedLaborCost | decimal |
| LegacyPartsCost | decimal |
| LegacyLaborCost | decimal |
| LegacyEstimatedTotalCost | decimal |
| RawTextbox38 | text |
| RawTextbox16 | text |
| Description | text |
| Details | text |
| AccountName | text |
| RawEquipmentId | text |
| FinancialSummarySHA256 | text |
| RecordId | text |
| ReportMonth | text |
| SourceSystem | text |
| ReportType | text |
| SourceFileName | text |
| SourceFileSHA256 | text |
| SourceRecordNumber | integer |
| CandidateRecordNumber | integer |
| LegacyCandidateSHA256 | text |
| CleanerVersion | text |
| ExportVersion | text |
| SchemaVersion | text |
| ValidationStatus | text |
| ReportingMonth | text |
| CandidateRevisionId | text |
| CandidateOutputSHA256 | text |
| CandidateCleanerVersion | text |
## ServiceOrders_History.csv

| Column | Type |
|---|---|
| EquipmentId | text |
| EquipmentName | text |
| ScheduledDate | date |
| CompletedDate | date |
| Location | text |
| Description | text |
| Status | text |
| RawStatus | text |
| EstimatedPrice | decimal |
| RawDescription | text |
| SourceMaintenanceTag | text |
| AccountName | text |
| SourceVendorName | text |
| RawCost | text |
| RawEquipmentId | text |
| RecordId | text |
| ReportMonth | text |
| SourceSystem | text |
| ReportType | text |
| SourceFileName | text |
| SourceFileSHA256 | text |
| SourceRecordNumber | integer |
| CandidateRecordNumber | integer |
| LegacyCandidateSHA256 | text |
| CleanerVersion | text |
| ExportVersion | text |
| SchemaVersion | text |
| ValidationStatus | text |
| ReportingMonth | text |
| CandidateRevisionId | text |
| CandidateOutputSHA256 | text |
| CandidateCleanerVersion | text |
## TMAWorkOrders_History.csv

| Column | Type |
|---|---|
| WorkOrderId | text |
| RequestDate | date |
| Requestor | text |
| Request | text |
| AssignedTo | text |
| RecordId | text |
| ReportMonth | text |
| SourceSystem | text |
| ReportType | text |
| SourceFileName | text |
| SourceFileSHA256 | text |
| SourceRecordNumber | integer |
| CandidateRecordNumber | integer |
| LegacyCandidateSHA256 | text |
| CleanerVersion | text |
| ExportVersion | text |
| SchemaVersion | text |
| ValidationStatus | text |
| ReportingMonth | text |
| CandidateRevisionId | text |
| CandidateOutputSHA256 | text |
| CandidateCleanerVersion | text |
## RepairFinancialSummaries.csv

| Column | Type |
|---|---|
| ReportMonth | text |
| ReportedLaborCost | decimal |
| ReportedPartsCost | decimal |
| ReportedTotalCost | decimal |
| ReportedRepairCount | integer |
| SourceRecordCount | integer |
| RetainedRepairCount | integer |
| KnownRepairTotalCost | decimal |
| UnavailableRepairCostCount | integer |
| RepairTotalDifference | decimal |
| SummaryComponentsDifference | decimal |
| ReconciliationStatus | text |
| SourceSystem | text |
| ReportType | text |
| SourceFileName | text |
| SourceFileSHA256 | text |
| LegacyCandidateSHA256 | text |
| CleanerVersion | text |
| ExportVersion | text |
| SchemaVersion | text |
| ValidationStatus | text |
| EstimatedLaborCostSum | decimal |
| EstimatedLaborCostMissingCount | integer |
| LegacyPartsCostSum | decimal |
| LegacyPartsCostMissingCount | integer |
| LegacyLaborCostSum | decimal |
| LegacyLaborCostMissingCount | integer |
| LegacyEstimatedTotalCostSum | decimal |
| LegacyEstimatedTotalCostMissingCount | integer |
| ReportingMonth | text |
| CandidateRevisionId | text |
| CandidateOutputSHA256 | text |
| CandidateCleanerVersion | text |
