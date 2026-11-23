# Confirmed acceptance defect — manifest JSON scalar types

**Status:** reproduced on main dc73a80 / V3 implementation shared with M2 f2718b3.
**Severity:** low validation/contract defect. **Application fix: not implemented;
owner approval required.** This testing-only PR adds detection and a reproduction.

## Reproduction (invented disposable copies only)

1. Generate the existing synthetic example into a NEW folder using
   examples/create_comparison_classification_demo.py.
2. Copy one completed comparison directory into another disposable test folder.
   Do not edit the original generated export or any departmental export.
3. In the copy's comparison_manifest.json, replace `"production_ready": false`
   with JSON integer `"production_ready": 0`.
4. The existing Python validate_comparison / --verify accepts the copy and returns
   an integer production_ready. The acceptance analyzer reports **FAIL** for
   development_contract. No CSV, canonical file or audit content was changed.
5. In another copy, leave production_ready false and replace a financial-summary
   rows_by_month count of JSON integer `1` with Boolean `true`. The existing
   verifier accepts it; the analyzer reports FAIL for dataset_repair_financial_summary.

Automated reproduction:

```powershell
uv run --frozen --all-extras python -m pytest tests/test_acceptance_analyzer.py -k type_coercion -q
```

The tests intentionally assert the current verifier behavior **and** independent
rejection. They document the defect; they do not convert it into an accepted
business limitation or change the verifier. When an owner-approved fix lands,
update these expectations with strict rejection regressions for every supported
contract version.

## Root cause and impact

comparison_export.validate_comparison compares the parsed manifest with a
recomputed Python dictionary. Python considers `False == 0` and `True == 1`,
including nested dictionary equality. Scalar JSON types therefore can differ
while the equality check succeeds. CSV field types and manifest scalar types
are separate assertions; the new analyzer checks both independently.

A Python integrity success does not guarantee the documented manifest Boolean /
integer types. Downstream consumers may reject such metadata. Actual Power Query
runtime behavior for these altered inputs was **not executed**. No changed
financial values, record loss, production approval, publishing or real-data damage
was demonstrated. Fresh valid synthetic bundles pass structural acceptance.

## Proposed minimal correction (requires approval)

Validate manifest Boolean fields with exact Boolean types/identity and all
row/month/lineage counts with `type(value) is int` (excluding bool), before comparing
values. Alternatively compare strict canonical JSON representations after schema
validation. Cover nested counts and V1/V2/V3 compatibility. Do not change generated
schemas, financial values, classification rules or approval semantics.

Risks: older hand-edited malformed bundles previously accepted by Python would be
rejected; legitimate generated bundles should remain valid. Test altered scalar
types, normal manifests, all versions, integrity failures, Power Query contract
compatibility and cleanup. Do not infer that every canonical-verifier field has
this issue; some existing canonical gates already use strict identity checks.

Broad Vac/ICE/Trash matches, earlier Vac capture of Kaivac, source-name conflicts,
ID aliases, missing costs and provisional Building membership are separately
recorded **REVIEW** limitations, not this code defect. Actual business accuracy,
Power BI execution and native Windows acceptance still need their own evidence.
