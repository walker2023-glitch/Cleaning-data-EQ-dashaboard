# Automated V3 and employee-interface acceptance

## Current execution — November 24, 2026

Milestone 2 and 3a are now merged (main b23a5e6, PR #31). The workflow tests the
exact pushed/PR SHA; manual dispatch may select a reviewed ref. The runner requires
**phase 55** plus monthly-check identities and fresh-process restart when the selected
checkout contains `monthly_update.py`. A separately selected original M2 checkout
still requires its complete phase-51 smoke. Use a NEW output directory and avoid
concurrent GUI checks on the same display. See [current review evidence](completion_readiness/README.md).

## Original testing-only implementation record

This testing-only feature adds no application code, rules, schemas or dependencies.
Verified main: `dc73a80a4ecbbe038f687c7735887bb1a210f644`.
Milestone 2 is **not on main** at this check; its pushed review commit is
`f2718b384f0c2ce7730239ee872f5da1b9d101a8`. Tests for that interface use a separate
checkout pinned to that commit. This PR targets main and does not carry or merge
the pending UI implementation. After owner merge, select the reviewed new main
commit explicitly; do not infer that old test results certify a new checkout.

## Read-only analyzer

From a frozen project environment (Python 3.12):

```powershell
uv sync --frozen --all-extras
uv run --frozen --all-extras python tools/acceptance/analyze_v3.py --comparison C:\EDM-Test\comparison --canonical C:\EDM-Test\snapshot --output C:\EDM-Test-Reports\new-run
```

Optionally add `--building-dimension C:\EDM-Test\ApprovedBuilding.csv`. The CSV must
have an exact **Building** text column; additional columns are ignored. Keys are
compared verbatim: no trimming, case folding, numeric casting, alias inference or
correction. Duplicate/blank dimension keys and unmatched/ambiguous fact references
require review. Supplying a CSV does not authenticate departmental approval.

Supply exactly one completed V3 bundle and its associated canonical snapshot.
V1/V2, staging directories, missing/unexpected files, unknown rule versions,
malformed/duplicate headers/JSON keys and invalid types are rejected. Linked paths
and UNC input/report paths are rejected. The associated six canonical files must
match the retained canonical bytes and manifest fingerprint. Never pass a candidate
store as either input. Inputs are only read, not cleaned, migrated, repaired or
opened through a candidate database. File bytes are checked again after analysis.

`--output` must be a **new** separate directory, with no overlap with any input
or its ancestors. It writes acceptance.json and acceptance.md, never overwrites
existing reports, and cleans only its newly owned directory on a caught write
failure. Abrupt process/OS termination can leave partial report files; regenerate
into a different new directory. Without --output, stdout is JSON; --format markdown
selects Markdown. Do not redirect stdout over an input file. No network operation
or data upload exists in the utility. Keep reports private even though cell values
are redacted.

Exit codes: **0** means no verified structural failure, including REVIEW/NOT TESTED;
**1** means FAIL; **2** means invalid/unavailable report destination or usage.
Exit 0 is **not departmental acceptance or production approval**. JSON always has
business_approved=false. Importing the analyzer directly returns the same report.
Its core is standard-library-only; if application verifiers are unavailable, that
additional check is NOT TESTED, not silently passed.

## What is independently checked

The analyzer has frozen V3/canonical schemas and independent test references in
tools/acceptance/contracts.py and reference.py. It does **not** use the producer's
projector, enrichment or classifiers to derive expected business records. Frozen
references intentionally implement the existing provisional compatibility policy;
a future version requires a reviewed new reference, not automatic discovery.
The application's existing read-only verifiers are an additional check.

- File/audit/warning hashes, ordered headers, declared types, monthly/total counts,
  version/purpose gates and association to the separately supplied canonical copy.
- Every ordered original occurrence, including repeated records; original names,
  descriptions, tags, locations and all unchanged fields. Normalized IDs retain
  leading zeros. Missing/unsupported formats remain distinct from invalid assets.
- Unique/nonblank observed equipment lookup, every fact-to-lookup key/name/type,
  most-recent nonblank names, stable ties, competing-name flags, source observations
  and observation counts. Blank-ID transactions stay in facts without fake assets.
- Complete fact and many-to-one equipment lineage: dataset/CSV ordinal, RecordId,
  candidate/source/summary provenance. Repeated records cannot vanish behind sums.
- Evidence-based maintenance at each occurrence, by report/month, preserving four
  labels and prioritized source evidence. Contradictions, negation, uncertain
  wording and unsupported tags cannot silently become Needed Repair.
- Unresolved/ambiguous buildings, unchanged Location, exact optional dimension
  matches. No authoritative Building_Dim knowledge is invented.
- Separate per-field repair counts/hours/reported/estimated/legacy financial
  comparisons, decimal totals and null counts; Service/TMA counts by month.
  A null-to-zero replacement fails even when aggregate numeric totals match.

Tests deliberately rewrite hashes/counts after corrupting a copy and stub the
application verifier to PASS. Independent comparisons must still fail. Passing
hashes alone is never business accuracy or authoritative source authentication.

## Reports, privacy and interpretation

Both formats include an executive summary, exact check counts, metrics, actionable
next steps and input manifest/dimension fingerprints. References use public dataset
filenames and **one-based parsed CSV record ordinals**, not physical text lines.
Reports do not repeat literal equipment IDs/names, locations, descriptions, private
paths, candidate identifiers or exception text. Inspect the referenced input/audit
rows privately for actual values. References are capped at 20 per finding, with
exact total/truncation indicators; all occurrences still participate in checks.
Monetary amounts are not echoed: field equality, separate total equality and null
counts provide the comparison evidence. The tool loads the selected bundle into
memory, like the current application verifier.

| Status | Meaning |
|---|---|
| PASS | Specified structural invariant verified against available evidence |
| REVIEW | Structurally valid data/policy needs departmental judgment |
| FAIL | Structural invariant violated or inputs rejected; investigate on a copy |
| NOT TESTED | Evidence, software, authorization or environment unavailable |

REVIEW includes name conflicts, ID collisions/unsupported formats, missing costs,
uncertain maintenance, unresolved/unmatched/ambiguous Buildings, broad Vac/ICE/Trash
matches, Kaivac's earlier Vac precedence, and observed inventory limitations.
These are not automatically application defects. A failed check on an intentionally
corrupted synthetic copy is a successful analyzer test, not a newly discovered app
bug. Fresh valid synthetic bundles have zero structural failures. One application
manifest scalar-type validation gap was reproduced on altered disposable copies;
see [reproduction, impact and proposed correction](acceptance_defects.md). No app
fix was implemented. Future defects also require owner approval before fixes.

Business accuracy, dimension authority, actual M/DAX/visuals and employee acceptance
remain NOT TESTED without their separate evidence. Reports are deterministic for
unchanged inputs/reference code; they deliberately contain no run timestamp.
[Invented example JSON](examples/acceptance_v3_synthetic.json) and
[Markdown](examples/acceptance_v3_synthetic.md) contain only synthetic evidence.

## Repeatable synthetic desktop run

Native Tk/CustomTkinter is not a web page, so Playwright is inappropriate. Existing
real-Tk widget tests and the phase-51/restart harness already exercise startup,
navigation, Settings History, multi-month processing, correction/save separation,
results/warnings, canonical snapshots and V3. Reusing them avoids adding pywinauto
or another dependency. Five focused M2 cases run in separate processes; the full
root regression remains the existing .github/run_tests.py workflow.

Create a separate reviewed M2 checkout; do not change branches in a checkout with
unsaved work. For example, from the root repository:

```powershell
git worktree add --detach ..\EDM-Acceptance-App f2718b384f0c2ce7730239ee872f5da1b9d101a8
uv run --frozen --all-extras python tools/acceptance/run_synthetic.py --app-checkout ..\EDM-Acceptance-App --output data\new-synthetic-acceptance --desktop
```

Every run requires a NEW workspace. Use a short trusted local writable parent
on Windows; conservative existing path guards still apply (CI uses runner.temp/ea). It accepts no departmental input or candidate
store paths. It generates invented inputs, two deterministic exports, a data
acceptance report, fixed 18/12/13/6/3 table controls, six missing reported costs and
a known text-ID control. It records application Git HEAD/provenance, platform and
source/resource equality before/after. Logs from subprocesses are captured rather
than echoing source values. GUI test JUnit and smoke evidence are synthetic only.
An unavailable/unusable display or missing M2 interface is NOT TESTED; explicitly
requested desktop coverage then exits **3**, not a false success or app defect.
Any failed test exits 1. No retries or skips are converted into passes.

For native Windows executable evidence, build the **selected app checkout** first:

```powershell
Push-Location ..\EDM-Acceptance-App
.\packaging\build.ps1
Pop-Location
uv run --frozen --all-extras python tools/acceptance/run_synthetic.py --app-checkout ..\EDM-Acceptance-App --output C:\EDM-Test\new-run --desktop --executable ..\EDM-Acceptance-App\dist\EquipmentDataManager\EquipmentDataManager.exe
```

The runner records the executable SHA-256, checks successful exit and the complete selected-checkout phase (55 for 3a,
51 for the original M2 checkout) plus fresh-process restore, and preserves all five widget outcomes. Build/source
association depends on using that checkout; a hash alone is not a signed build
attestation. Linux needs a usable DISPLAY (CI uses existing xvfb-run). Never run
GUI suites/smokes concurrently on the same display. Windows DPI, accessibility,
managed-PC policy and first-time employee comprehension still need a short human
walkthrough on the intended computer.

.github/workflows/acceptance.yml runs on Ubuntu/Windows using only synthetic data,
with the M2 commit pinned above or an explicitly chosen manual app_ref. It also
runs that selected application checkout's complete existing regression suite;
the quick local synthetic runner itself runs the five focused UI cases, not the
full application suite. Windows
reuses the selected checkout's build.ps1. It has read-only repository permissions,
no secrets, no report/data uploads and sanitized summary logging. The existing
root tests.yml independently runs the complete regression at this testing head.
Do not call scheduled/pending CI passed without observed exact-commit results.

## Backup-PBIX procedure and remaining human checks

No PBIX was supplied and this Linux environment cannot run Power BI Desktop. The
smallest safe approach is the owner's existing Windows Power BI Desktop and a
separately saved backup copy; no new automation software or permission is needed.
No PBIX automation or relationship/query/measure modification is performed here.

1. Choose a completed snapshot/comparison pair on trusted local storage, run the
   analyzer, preserve the report/fingerprints and resolve FAIL findings first.
   Supply the approved Building dimension if available. Do not rewrite sources to
   clear a REVIEW finding. Confirm missing months, source trust and business rules.
2. Open a newly saved backup PBIX, confirm its filename and keep production closed.
   Preserve a baseline of original query/relationship/DAX/visual configuration.
   Disable automatic relationship creation for the new disconnected comparison.
3. Follow comparison_exports_v3.md at the selected app commit: import the existing
   fnReadComparisonPreviewV3 helper and five NEW disconnected comparison queries,
   pointing to exactly one completed comparison folder. Do not change existing
   sources, relationships, queries or measures automatically. Do not import audit.
4. Check five table counts against report dataset/month metrics. Confirm EquipmentId
   is text, including known leading-zero cases; numeric/date nulls stay null and
   NameConflict is logical. Existing Python/helper schema-contract tests are static
   evidence, **not actual M evaluation**. Record all refresh/type errors privately.
5. Compare fact keys/names/types with Equipment and unmatched/duplicate Building
   keys. Inspect existing Building_Dim/Equipment relationships/cardinality/filter
   directions without altering them. Treat any relationship change as a separate
   explicit owner decision, not something an automation script fixes.
6. Compare canonical/V3 counts, repair hours and each financial meaning separately;
   reported totals are not parts plus another labor estimate. Check null counts,
   partial totals and accepted warnings; do not allocate monthly totals to repairs.
7. Compare existing important measures and visuals with the recorded baseline,
   preserving DAX, date-only fields, March exclusions, TMA Requests/Work Order grain
   and actual month coverage. Explain old lexical MAXX versus latest-name selection,
   old Preventative versus Preventive Maintenance, and extra uncertainty labels.
8. Record Power BI build, reviewed Git SHA, input fingerprints, expected/actual
   controls, errors, relationship/DAX/visual comparison and owner decision privately.
   No publish, production refresh, activation or SharePoint write is authorized.

Nothing begins Milestone 3a/3b or merges any PR. Next gate is owner review of this
workflow, hosted Windows evidence and the remaining business/backup-PBIX checks.
