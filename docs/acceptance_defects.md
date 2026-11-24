# Confirmed acceptance defect — manifest JSON scalar types

**Current status — November 24, 2026:** owner approved the narrow strict metadata
fix. Implementation on `feature/strict-manifest-metadata` is prepared for review;
not merged by this work. No schema, generated export, financial or classification
change. Comparison verification now compares canonical JSON representations, so
Boolean/integer/float aliases differ at every nesting level. Canonical verification
also checks existing Boolean flags and integer/nullable-integer counts explicitly.
Valid generated canonical and V1/V2/V3 manifests retain their existing contracts.

**Historical reproduction:** main dc73a80 / V3 shared with M2 f2718b3 accepted the
malformed scalar types below. The original finding was a low-severity validation
contract defect; it did not establish data loss or production approval.

## Historical reproduction (invented disposable copies only)

1. Generate the existing synthetic example into a NEW folder using
   examples/create_comparison_classification_demo.py.
2. Copy one completed comparison directory into another disposable test folder.
   Do not edit the original generated export or any departmental export.
3. In the copy's comparison_manifest.json, replace `"production_ready": false`
   with JSON integer `"production_ready": 0`.
4. Before this fix, Python validate_comparison / --verify accepted the copy and returned
   an integer production_ready. The acceptance analyzer reports **FAIL** for
   development_contract. No CSV, canonical file or audit content was changed.
5. In another copy, leave production_ready false and replace a financial-summary
   rows_by_month count of JSON integer `1` with Boolean `true`. Before this fix, the
   verifier accepted it; the analyzer reports FAIL for dataset_repair_financial_summary.

Automated reproduction:

```powershell
uv run --frozen --all-extras python -m pytest tests/test_acceptance_analyzer.py -k type_coercion -q
```

The approved regressions now require application rejection **and** independent
analyzer rejection. `tests/test_manifest_metadata_types.py` also covers valid/key-reordered
V1/V2/V3 manifests, nested dataset/month/lineage/warning counts, canonical flags,
nullable metadata and retained canonical evidence. Read-only verification preserves
all CSV bytes; malformed hand-edited metadata previously accepted is rejected.

## Root cause and impact

Before the approved fix, comparison_export.validate_comparison compared the parsed
manifest with a recomputed Python dictionary. Python considers `False == 0` and `True == 1`,
including nested dictionary equality. Scalar JSON types therefore can differ
while the equality check succeeds. CSV field types and manifest scalar types
are separate assertions; the new analyzer checks both independently.

Before the fix, a Python integrity success did not guarantee documented manifest
Boolean/integer types. Downstream consumers may reject such metadata. Actual Power Query
runtime behavior for these altered inputs was **not executed**. No changed
financial values, record loss, production approval, publishing or real-data damage
was demonstrated. Fresh valid synthetic bundles pass structural acceptance.

## Approved minimal correction and compatibility

The approved approach validates canonical Boolean fields with exact Boolean types and
integer/nullable-integer counts with `type(value) is int` (excluding bool). Comparisons
use strict canonical JSON representations against the existing recomputed expected
manifest, including nested row/month/lineage/warning counts. No generated schema,
financial value, classification rule or approval semantic changes.

Risks: older hand-edited malformed bundles previously accepted by Python would be
rejected; legitimate generated bundles should remain valid. Test altered scalar
types, normal manifests, all versions, integrity failures, Power Query contract
compatibility and cleanup. Do not infer that every canonical-verifier field has
this issue; some existing canonical gates already use strict identity checks.

Broad Vac/ICE/Trash matches, earlier Vac capture of Kaivac, source-name conflicts,
ID aliases, missing costs and provisional Building membership are separately
recorded **REVIEW** limitations, not this code defect. Actual business accuracy,
Power BI execution and native Windows acceptance still need their own evidence.
