# Milestone B — equipment inventory foundation (design only)

No `CompuClean Equipment List by Location.csv` or approved sanitized raw/expected
inventory pair is available. No inventory adapter, parsing aliases, status semantics
or model relationship is enabled. Inventory remains outside the three-report monthly
completeness contract. Finish the v2 real-data Desktop acceptance before unrelated
implementation. Building_Dim columns/keys are also not supplied.

## Existing code evidence and limitations

The preserved legacy/clean/list_clean.py searches for EquipmentId/Name-like headers,
uses guessed offsets, pandas inference, drops duplicate equipment IDs, merges all
cleaned history and falls back from CurrentValue to Cost. It imports missing
`dashboard.taxonomy` and an unsupplied Type.csv lookup. This is code evidence, not
proof of the current location export layout or an approved inventory/finance policy.
Do not enable it merely because aliases look plausible. In particular, ID inference,
latest-purchase deduplication, accumulated historical counts and financial fallback
must not be adopted without verified fixtures and decisions.

## Proposed normalized snapshot contract — not raw-column guesses

| Proposed output | Meaning / validation |
|---|---|
| EquipmentId | Required literal text, preserving leading zeros; unique only after duplicate review for this snapshot |
| EquipmentName | Source equipment description, preserved |
| RawLocation | Exact source location, always retained |
| BuildingKey / Building / Room | Nullable, from a versioned approved map; no inferred key compatibility |
| LocationResolution / LocationMapVersion | Mapped, building-only, missing or unresolved; mapping evidence/version |
| RawStatus / OnlineStatus | Preserve source status; proposed online/offline/unknown values only after source semantics confirmed |
| PurchaseDate / SerialNumber | Nullable ISO date/text only if genuinely available and verified |
| SnapshotId / SnapshotDate | Explicit source snapshot identity/date; never use file modification time as business date |
| SourceFileName / SourceFileSHA256 / SourceRecordNumber | File/occurrence provenance, no hardcoded personal path |
| ExportVersion / SchemaVersion / ValidationStatus | Versioned contract and candidate state; no invented approval |

No financial interpretation is proposed for undocumented Cost/CurrentValue columns.
Confirm source layout, preambles, group/summary rows, encoding, date/status/duplicate
semantics and expected counts before defining an adapter. Preserve raw source files.

## Maintainable location mapping

Start with a reviewed exact-label map containing RawLocation, approved BuildingKey,
BuildingName, Room/SpaceLabel, mapping version/effective date, reviewer/evidence.
Keep normalization/aliases explicit; do not split at the first space. Multiword
buildings, stairs, shops and building-only entries need named reviewed examples.
Conflicting/duplicate map keys fail; unmapped text remains visible in an unresolved
location table with null building/room keys. Show unresolved counts in the matrix.
Do not silently drop unknown locations or invent Room from digits in a building name.
Obtain a nonsecret authorized Building_Dim key/name export and collision policy first.

## Snapshot identity, selection and changes

Store immutable candidate snapshot artifacts with input/output hashes, snapshot date,
map/schema versions and counts. Select one current snapshot explicitly; keep prior
snapshots outside the current inventory ingestion root. Power BI's inventory table
must read only that current selection, never append historical snapshots as stock.
Detect duplicate IDs within the selected snapshot and block ambiguous dimension
selection rather than keeping the first row silently. Compare validated ID sets
between snapshots: additions, no-longer-observed IDs and location/status changes.
No-longer-observed and offline are not proof of physical deletion/disposal. Corrections
to the same snapshot need explicit revision review and preserve prior selections.

## Proposed model and matrix

Building → Room → EquipmentName → EquipmentId should use the selected current
inventory snapshot with unresolved-location visibility. Propose a one-row-per-validated
EquipmentId current dimension and one-to-many links to repair/service facts only
after uniqueness and exact text-key comparisons (including unmatched IDs) pass.
Do not strip/pad zeros or use TMA WorkOrderId as equipment identity.

Current-location inventory analysis differs from event-time repair/service location.
Keep source historical locations; do not rewrite old facts when equipment moves.
Review separate location dimension roles and filter paths with the model owner;
avoid active ambiguous bidirectional/many-to-many joins. Historical inventory analysis
needs a separately designed dated-snapshot fact rather than an appended current dimension.

## Inputs and acceptance before implementation

Supply an authorized sanitized raw/expected inventory pair with leading-zero IDs,
multiple buildings/rooms/stairs/shops, unknown and building-only locations, duplicate
IDs, online/offline/blank statuses and two dated snapshots showing moves/additions/
no-longer-observed equipment. Include exact expected counts and status/date meanings,
Building_Dim keys and a reviewed location map. Confirm whether taxonomy is needed;
if reusing the original module, provide its missing helpers/lookup. Next work should
implement only this verified contract with synthetic regressions and no Graph access.
