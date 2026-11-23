# Equipment Data Manager acceptance report

**Overall: REVIEW**

41 PASS, 8 REVIEW, 0 FAIL, 4 NOT TESTED. Structural validation is not business approval.

Business approval: **not established**. REVIEW findings are not automatically code defects.

| Check | Status | Finding | Next step |
|---|---|---|---|
| development_contract | PASS | Export is explicitly development-only, not production approval. |  |
| source_association | PASS | Retained canonical bytes match the separately supplied snapshot. |  |
| canonical_contract | PASS | Canonical input remains a complete unapproved historical snapshot. |  |
| manifest_context | PASS | Selection interval, canonical contract and equipment monthly-count basis match the associated snapshot. |  |
| dataset_repairs | PASS | Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference. |  |
| canonical_repairs | PASS | Canonical file schema/hash/counts match its manifest. |  |
| dataset_service_orders | PASS | Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference. |  |
| canonical_service_orders | PASS | Canonical file schema/hash/counts match its manifest. |  |
| dataset_tma_work_orders | PASS | Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference. |  |
| canonical_tma_work_orders | PASS | Canonical file schema/hash/counts match its manifest. |  |
| dataset_repair_financial_summary | PASS | Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference. |  |
| canonical_repair_financial_summary | PASS | Canonical file schema/hash/counts match its manifest. |  |
| dataset_equipment | PASS | Dataset hash, ordered schema, declared types and total/monthly counts match the frozen V3 reference. |  |
| canonical_report_hash | PASS | Canonical compatibility report hash matches. |  |
| audit_integrity | PASS | All audit/warning hashes, ordered audit schemas and lineage counts match. |  |
| equipment_unique | PASS | Lookup keys are unique and nonblank. |  |
| equipment_resolution | PASS | Lookup names/types/months/counts/conflicts/order independently follow the documented most-recent-name policy. |  |
| record_counts_repairs | PASS | Canonical and V3 transaction/summary counts match by month; repeated occurrences are retained. |  |
| ordered_projection_repairs | PASS | Every ordered occurrence independently matches canonical values plus documented enrichment; no row deduplication, reordering or value replacement. |  |
| lookup_fact_repairs | PASS | Every nonblank fact key has a lookup with the same resolved name/type. |  |
| financial_repairs | PASS | Each count/hour/financial field is compared separately, including nulls and decimal totals. Reported amounts are never combined with estimates. |  |
| record_counts_service_orders | PASS | Canonical and V3 transaction/summary counts match by month; repeated occurrences are retained. |  |
| ordered_projection_service_orders | PASS | Every ordered occurrence independently matches canonical values plus documented enrichment; no row deduplication, reordering or value replacement. |  |
| lookup_fact_service_orders | PASS | Every nonblank fact key has a lookup with the same resolved name/type. |  |
| financial_service_orders | PASS | Each count/hour/financial field is compared separately, including nulls and decimal totals. Reported amounts are never combined with estimates. |  |
| record_counts_tma_work_orders | PASS | Canonical and V3 transaction/summary counts match by month; repeated occurrences are retained. |  |
| ordered_projection_tma_work_orders | PASS | Every ordered occurrence independently matches canonical values plus documented enrichment; no row deduplication, reordering or value replacement. |  |
| record_counts_repair_financial_summary | PASS | Canonical and V3 transaction/summary counts match by month; repeated occurrences are retained. |  |
| ordered_projection_repair_financial_summary | PASS | Every ordered occurrence independently matches canonical values plus documented enrichment; no row deduplication, reordering or value replacement. |  |
| financial_repair_financial_summary | PASS | Each count/hour/financial field is compared separately, including nulls and decimal totals. Reported amounts are never combined with estimates. |  |
| complete_lineage | PASS | Lineage maps every output occurrence and equipment contributor to its canonical dataset/ordinal, record ID, revision and hashes. |  |
| classification_source_evidence | PASS | Every classification/conflicting name retains exact source tags/descriptions, canonical source references and independently checked rule evidence. |  |
| maintenance_evidence_consistency | PASS | Maintenance labels independently match prioritized source evidence; contradictory/uncertain evidence cannot silently become Needed Repair. |  |
| maintenance_contract | PASS | Maintenance labels use the four-value contract, preserving Unclassified and Needs Review. |  |
| name_conflicts | REVIEW | Conflicting verbatim equipment names; use referenced observation audit rows to inspect competing names and sources. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| id_collisions | REVIEW | Distinct supported original IDs normalize to one key; review aliases before joining. No observations were merged. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| id_missing | PASS | Missing IDs remain in fact tables without fictitious lookup records. |  |
| id_unsupported | REVIEW | Unsupported ID formats are retained literal text; unsupported does not mean an invalid identifier. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| equipment_other | PASS | No equipment rule matched; Other requires departmental review. |  |
| broad_equipment_keywords | REVIEW | Vac, ICE or Trash substring matches may be overbroad; compatibility rules were not changed. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| kaivac_precedence | PASS | Kaivac matches the earlier Vac rule; this accepted compatibility limitation is not a code failure. |  |
| building_missing | PASS | Location is blank; no Building was invented. |  |
| building_unresolved | PASS | Building remains unresolved; check source evidence and the departmental dimension. |  |
| building_ambiguous | REVIEW | Location is ambiguous under the conservative Building policy; no aliases or corrections applied. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| maintenance_uncertain | REVIEW | Unclassified or Needs Review remains explicit; inspect source evidence rather than forcing Needed Repair. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| missing_repair_costs | REVIEW | Missing reported repair costs stay blank. Partial known totals are not complete source totals. | Review referenced records in the private audit evidence with the data owner; no automatic correction. |
| building_dimension | NOT TESTED | No Building dimension supplied; membership and unmatched/ambiguous dimension keys cannot be established. | Rerun with an owner-approved CSV containing the exact text Building column. |
| inventory_authority | REVIEW | Observed equipment covers only the selected history; it is not an authoritative complete inventory. | Confirm lookup coverage and aliases with the department. |
| application_verifiers | PASS | Additional existing read-only canonical/comparison verifiers; independent assertions above do not depend on their verdict. | Use the frozen project environment. A verifier rejection needs investigation, not automatic repairs. |
| inputs_unchanged | PASS | All captured input bytes remain unchanged after analysis; no application write/generation API was called. |  |
| business_accuracy | NOT TESTED | Business accuracy, source completeness and departmental policy approval require independent human evidence. | Follow the documented Windows/backup-PBIX acceptance procedure and record separate evidence. |
| power_bi_runtime | NOT TESTED | Actual five-table M import, DAX, visuals and relationships have not been executed by this analyzer. | Follow the documented Windows/backup-PBIX acceptance procedure and record separate evidence. |
| native_desktop | NOT TESTED | This data analyzer does not execute Windows or native desktop UI tests. | Follow the documented Windows/backup-PBIX acceptance procedure and record separate evidence. |

## Evidence identity

```json
{
  "input_fingerprints": {
    "building_dimension_sha256": null,
    "canonical_manifest_sha256": "b9329c0007ea85cad8867d8637e7c15f3cc1725936ae6b513acdc1809a50e1cc",
    "comparison_manifest_sha256": "82bca3828232873d6e4f767ad2134c4b08c89baaa170626cba9aadd11f968aa5"
  },
  "report_schema": "edm-acceptance-v1"
}
```

## Detailed counts and redacted references

### dataset_repairs

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "rows": 18,
    "rows_by_month": {
      "2026-01": 3,
      "2026-02": 3,
      "2026-03": 3,
      "2026-04": 3,
      "2026-05": 3,
      "2026-06": 3
    }
  }
}
```

### dataset_service_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "rows": 12,
    "rows_by_month": {
      "2026-01": 2,
      "2026-02": 2,
      "2026-03": 2,
      "2026-04": 2,
      "2026-05": 2,
      "2026-06": 2
    }
  }
}
```

### dataset_tma_work_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "rows": 13,
    "rows_by_month": {
      "2026-01": 2,
      "2026-02": 2,
      "2026-03": 2,
      "2026-04": 2,
      "2026-05": 2,
      "2026-06": 3
    }
  }
}
```

### dataset_repair_financial_summary

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "rows": 6,
    "rows_by_month": {
      "2026-01": 1,
      "2026-02": 1,
      "2026-03": 1,
      "2026-04": 1,
      "2026-05": 1,
      "2026-06": 1
    }
  }
}
```

### dataset_equipment

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "rows": 3,
    "rows_by_month": {
      "2026-01": 3
    }
  }
}
```

### equipment_unique

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "lookup_rows": 3
  }
}
```

### record_counts_repairs

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "canonical": 18,
    "comparison": 18,
    "rows_by_month": {
      "2026-01": 3,
      "2026-02": 3,
      "2026-03": 3,
      "2026-04": 3,
      "2026-05": 3,
      "2026-06": 3
    }
  }
}
```

### ordered_projection_repairs

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "mismatched_occurrences": 0
  }
}
```

### financial_repairs

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "EstimatedLaborCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyEstimatedTotalCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyLaborCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyPartsCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "RepairCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "RepairPersonHours": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "ReportedTotalCost": {
      "canonical_nulls": 6,
      "comparison_nulls": 6,
      "equal_cells": true,
      "equal_totals": true
    }
  }
}
```

### record_counts_service_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "canonical": 12,
    "comparison": 12,
    "rows_by_month": {
      "2026-01": 2,
      "2026-02": 2,
      "2026-03": 2,
      "2026-04": 2,
      "2026-05": 2,
      "2026-06": 2
    }
  }
}
```

### ordered_projection_service_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "mismatched_occurrences": 0
  }
}
```

### financial_service_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "EstimatedPrice": {
      "canonical_nulls": 12,
      "comparison_nulls": 12,
      "equal_cells": true,
      "equal_totals": true
    }
  }
}
```

### record_counts_tma_work_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "canonical": 13,
    "comparison": 13,
    "rows_by_month": {
      "2026-01": 2,
      "2026-02": 2,
      "2026-03": 2,
      "2026-04": 2,
      "2026-05": 2,
      "2026-06": 3
    }
  }
}
```

### ordered_projection_tma_work_orders

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "mismatched_occurrences": 0
  }
}
```

### record_counts_repair_financial_summary

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "canonical": 6,
    "comparison": 6,
    "rows_by_month": {
      "2026-01": 1,
      "2026-02": 1,
      "2026-03": 1,
      "2026-04": 1,
      "2026-05": 1,
      "2026-06": 1
    }
  }
}
```

### ordered_projection_repair_financial_summary

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "mismatched_occurrences": 0
  }
}
```

### financial_repair_financial_summary

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "EstimatedLaborCostMissingCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "EstimatedLaborCostSum": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "KnownRepairTotalCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyEstimatedTotalCostMissingCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyEstimatedTotalCostSum": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyLaborCostMissingCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyLaborCostSum": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyPartsCostMissingCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "LegacyPartsCostSum": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "RepairTotalDifference": {
      "canonical_nulls": 6,
      "comparison_nulls": 6,
      "equal_cells": true,
      "equal_totals": true
    },
    "ReportedLaborCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "ReportedPartsCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "ReportedRepairCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "ReportedTotalCost": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "RetainedRepairCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "SourceRecordCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "SummaryComponentsDifference": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    },
    "UnavailableRepairCostCount": {
      "canonical_nulls": 0,
      "comparison_nulls": 0,
      "equal_cells": true,
      "equal_totals": true
    }
  }
}
```

### complete_lineage

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "actual_links": 79,
    "expected_links": 79
  }
}
```

### classification_source_evidence

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "actual_observations": 30,
    "expected_observations": 30
  }
}
```

### maintenance_evidence_consistency

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "suspicious_classifications": 0
  }
}
```

### maintenance_contract

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "by_report_month": [
      {
        "classification": "Needed Repair",
        "month": "2026-01",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needed Repair",
        "month": "2026-02",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needed Repair",
        "month": "2026-03",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needed Repair",
        "month": "2026-04",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needed Repair",
        "month": "2026-05",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needed Repair",
        "month": "2026-06",
        "report_type": "repairs",
        "rows": 3
      },
      {
        "classification": "Needs Review",
        "month": "2026-01",
        "report_type": "service_orders",
        "rows": 2
      },
      {
        "classification": "Needs Review",
        "month": "2026-02",
        "report_type": "service_orders",
        "rows": 2
      },
      {
        "classification": "Needs Review",
        "month": "2026-03",
        "report_type": "service_orders",
        "rows": 2
      },
      {
        "classification": "Needs Review",
        "month": "2026-04",
        "report_type": "service_orders",
        "rows": 2
      },
      {
        "classification": "Needs Review",
        "month": "2026-05",
        "report_type": "service_orders",
        "rows": 2
      },
      {
        "classification": "Needs Review",
        "month": "2026-06",
        "report_type": "service_orders",
        "rows": 2
      }
    ]
  }
}
```

### name_conflicts

```json
{
  "evidence": [
    {
      "dataset": "Repairs_History.csv",
      "record": 1
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 2
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 3
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 4
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 5
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 6
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 7
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 8
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 9
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 10
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 11
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 12
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 13
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 14
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 15
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 16
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 17
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 18
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 1
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 3
    }
  ],
  "evidence_total": 24,
  "evidence_truncated": true,
  "metrics": {
    "affected_observations": 24
  }
}
```

### id_collisions

```json
{
  "evidence": [
    {
      "dataset": "Repairs_History.csv",
      "record": 1
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 3
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 4
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 6
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 7
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 9
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 10
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 12
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 13
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 15
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 16
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 18
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 1
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 3
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 5
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 7
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 9
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 11
    }
  ],
  "evidence_total": 18,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 18
  }
}
```

### id_missing

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 0
  }
}
```

### id_unsupported

```json
{
  "evidence": [
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 2
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 4
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 6
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 8
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 10
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 12
    }
  ],
  "evidence_total": 6,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 6
  }
}
```

### equipment_other

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 0
  }
}
```

### broad_equipment_keywords

```json
{
  "evidence": [
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 2
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 4
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 6
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 8
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 10
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 12
    }
  ],
  "evidence_total": 6,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 6
  }
}
```

### kaivac_precedence

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 0
  }
}
```

### building_missing

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 0
  }
}
```

### building_unresolved

```json
{
  "evidence": [],
  "evidence_total": 0,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 0
  }
}
```

### building_ambiguous

```json
{
  "evidence": [
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 2
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 4
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 6
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 8
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 10
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 12
    }
  ],
  "evidence_total": 6,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 6
  }
}
```

### maintenance_uncertain

```json
{
  "evidence": [
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 1
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 2
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 3
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 4
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 5
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 6
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 7
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 8
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 9
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 10
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 11
    },
    {
      "dataset": "ServiceOrders_History.csv",
      "record": 12
    }
  ],
  "evidence_total": 12,
  "evidence_truncated": false,
  "metrics": {
    "affected_observations": 12
  }
}
```

### missing_repair_costs

```json
{
  "evidence": [
    {
      "dataset": "Repairs_History.csv",
      "record": 2
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 5
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 8
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 11
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 14
    },
    {
      "dataset": "Repairs_History.csv",
      "record": 17
    }
  ],
  "evidence_total": 6,
  "evidence_truncated": false,
  "metrics": {
    "rows": 6
  }
}
```
