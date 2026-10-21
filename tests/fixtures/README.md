# Test fixture provenance

`synthetic/service_orders_february_2026.csv` is a newly authored sanitized shape
regression for the user-supplied ten-column, five-record BOM export. Account,
equipment names, locations and descriptions are invented; IDs are synthetic,
including the user-requested `000439` example. The repeated count and February
date shapes match the observed structure. The paired expected CSV records the
specified mapping and unchanged cleaner rules, not a trusted departmental golden.
The actual uploaded report and local validation outputs are not committed.

`synthetic/` contains invented, nonprivate values in column layouts observed in
the uploaded source. Expected CSVs capture a small subset of the source behavior:
repairs calculate two hours at the existing 12.5 rate and omit an invalid date;
service retains a September scheduled/completed row and omits an August row;
requests omit a total row and an invalid date and format the surviving date.

M0 tests exercise unchanged in-memory transforms. M1 also exercises wrapper CSV
reading, the original repair writer, unchanged service serialization, and local
coordinator outputs/failures. These do not verify legacy disk entry points,
Microsoft integration, full schema support or business correctness.
They are not sanitized source exports, TMA evidence, approved golden files, or a
Power BI reconciliation baseline. No production data was used to create them.

Use `docs/inputs_needed.md` when supplying reviewed, authorized raw/expected pairs.
Document provenance, sanitizer, month, grain, exclusions, counts, totals and
tolerances alongside any later approved fixtures.
