# February 2026 Service Orders List layout fix

## Cause

M1 required `Cost` for every flat Service Orders List. The supplied ten-column
export has no `Cost` column, so the wrapper raised `missing_required_columns`
before it could call the original cleaner. UTF-8 BOM handling was already correct
and was not the cause. The original `service_row_clean.py` accepts missing cost:
its existing missing-money path emits a blank `Estimated Price`.

## Specific supported layout

The new adapter requires exactly this header set (column order may vary):

```text
AccountName2,EquipmentId1,EquipmentName1,VendorName,ScheduledDate,CompletedDate,Name,Description,Textbox21,Textbox56
```

Blank/duplicate headers, malformed CSV, missing/extra columns for this new layout,
and inconsistent or unrecognized summary metadata still fail validation. This does
not enable arbitrary CSVs or make `Cost` optional in the older priced layout.

| Raw field | Expected cleaned field/handling |
|---|---|
| `EquipmentId1` | `Equipment Id`, read as text before numeric inference; retains `000439` |
| `EquipmentName1` | `Equipment Name` |
| `ScheduledDate` | `Sched. Date`, existing ISO date formatting |
| `CompletedDate` | `Completed Date`, existing ISO date formatting |
| `Name` | `Location`, per the original flat-list mapping |
| `Description` | `Description`, existing suffix/exclusion rules retained |
| `Textbox21` | `Status`, existing status rules retained |
| No cost field | Blank `Estimated Price`, with an explicit unavailable-price warning |
| `Textbox56` | Repeated report-count metadata; never a service record or a price |
| `AccountName2`, `VendorName` | Retained in original input; not added to the fixed eight-column output. Existing unmapped-column warning reports these two fields. |

The repeated `Total Service Orders: 5` cells must agree with each other and with
the number of raw records. They are checked once as a source count, not summed.
Source/retained counts are returned as metrics. Existing month, description and
date exclusions can still reduce retained rows for other inputs, with the existing
exclusion warning. A separate summary-only row is not part of this observed format;
it is rejected by the count check rather than silently discarded or fabricated.

Leading-zero protection is scoped to the new layout. Older priced-format parsing,
output schema and transformations remain unchanged. The original and vendored
cleaner scripts are untouched. The service wrapper version is advanced so existing
service outputs require the usual review before reprocessing; repair identity is
unchanged. No SharePoint or Power BI files are accessed or modified.

## Test in VS Code on Windows

1. Open the repository folder and select branch
   `feature/service-orders-february-layout` in Source Control (fetch first if needed).
2. In the integrated PowerShell terminal, using the project's uv/Python setup:

   ```powershell
   uv sync --frozen --all-extras
   uv run --frozen --all-extras pytest
   uv run --frozen --extra desktop equipment-data-manager-desktop --output-dir data/service-layout-review
   ```

   For Python debugging, select `.venv\Scripts\python.exe` as VS Code's interpreter.
3. In the app choose **Service Orders List**, then **Select local raw files** and
   select `tests/fixtures/synthetic/service_orders_february_2026.csv`. The built-in
   Load synthetic sample button still uses September; use the February fixture here.
4. Select **February 2026**, confirm the month, then **Preview Processing**. Expect
   five input/output rows, no unsupported-layout error, an unavailable-price warning
   and the existing production-accuracy warning.
5. Click **Process Reports**. Open the selected output folder and inspect the CSV
   in VS Code as text: five records, `000439`/`000007`, ISO dates, the eight expected
   columns and blank Estimated Price. Repeating the same file should skip it.

To exercise just the fix: `uv run --frozen --all-extras pytest tests/test_service_orders_export.py`.
Headless Linux full-suite runs require a display, e.g. `xvfb-run -a` before uv.
Keep actual departmental files and candidate outputs under an approved ignored
location such as `data/private/`, not in committed fixtures.

## Evidence and remaining accuracy gate

All 130 local tests pass, including the prior 117 and a real-widget February
preview/process regression. The supplied report was also checked locally: five
source records became five outputs, preserving the requested field values using
the original date/description/status rules, and its source bytes were unchanged.
Only aggregate outcomes are documented; the uploaded report is not committed.

The committed fixture uses invented account/equipment/location/description values,
the observed headers/BOM/date shape/count metadata, and the requested leading-zero
example. Its expected CSV is a code/mapping regression, **not** a trusted departmental
baseline. Full production accuracy remains unverified until comparison with an
approved expected cleaned result and baseline totals. TMA was blocked at this fix; the later multi-month follow-up
adds provisional XLSX candidates (see `format_compatibility.md`).
