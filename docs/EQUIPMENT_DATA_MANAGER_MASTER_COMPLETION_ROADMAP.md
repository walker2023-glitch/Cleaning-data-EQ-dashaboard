# Equipment Data Manager — Master Completion Roadmap

**Status:** Owner-approved product direction (planning rounds 1–5)  
**Document version:** 1.0 — 2026-11-12  
**Project:** `walker2023-glitch/Cleaning-data-EQ-dashaboard`  
**Last owner-confirmed merged baseline:** `eea5d01` (`main`, historical batch processing). **Verify current repository state before any work.**  
**Current in-progress work at planning time:** Historical Power BI Dataset Generator, on a separate feature branch; completion and merge are **not confirmed**.

> **Governing principle:** Build the simplest reliable, button-driven tool that coworkers can use after the original developer leaves. Technical sophistication is not a goal by itself. The owner approves milestones, scope, code fixes, merges, and production changes.

## 1. Product vision and definition of success

Equipment Data Manager is a Windows desktop application with a guided, approachable workflow inspired by the usability philosophy of the EMS Event Processor. A coworker without Python, Git, or Power BI expertise should be able to:

1. Point the application at a folder containing several months of downloaded or synced equipment reports.
2. Have the application discover months and report types automatically, identify already processed files, and explain missing/changed/problematic inputs.
3. Review what will be cleaned and what will be skipped, then confirm processing.
4. Produce or update a **combined, Power BI-compatible dataset** in a stable location, with an explicit review and activation step.
5. Repeat the routine next month through buttons, without editing Power Query, DAX, scripts, or source code.
6. Recover from ordinary errors using a short guide; escalate exceptional issues to a named maintainer.

**Primary goal:** Easy cleaning, combination, and dependable Power BI consumption.  
**Stretch goal:** One-click refresh from authorized SharePoint or a OneDrive-synced folder, with minimal manual downloads.  
**Target users:** Coworkers and successor employees after the owner leaves.  
**Finish line:** Installable Windows application, usable monthly workflow, user guide, troubleshooting and maintenance handoff—not merely a developer demonstration.

### Non-goals unless separately approved

- New analytics, labor forecasting, or dashboard redesign.
- Direct Microsoft Graph integration, cloud services, or new infrastructure beyond the minimum required.
- Expanded identity, approval, or publication systems merely because foundations already exist.
- Automatic edits to production PBIX, SharePoint, or approved data.
- Rewriting the existing cleaning engine or financial calculations without a separately approved reason.

Existing safeguards remain in place; avoiding new scope does **not** authorize weakening integrity or security protections.

## 2. Owner-confirmed product decisions

| Topic | Decision | Consequence |
|---|---|---|
| Workflow | **Guided** | Select folder → discover/preview → review plan → process → review output → confirm activation. |
| Employee skill level | No programming or Power BI knowledge needed for routine operation | UI and messages must use plain language; advanced details are optional. |
| Input | Multi-month folder | Automatically recognize year/month/report type, including existing SharePoint year/month layout. |
| Already processed files | Detect unchanged files | Skip equivalent candidates; changed files/corrections require review. |
| Error handling | Continue eligible work, flag issues | A bad report need not halt all cleaning; no silent omission from the active dataset. |
| Partial inclusion | Employee may choose months | Show exact months and report types included/excluded before activation. |
| Active Power BI location | Stable configurable path | No monthly Power Query edits for ordinary use. |
| Destination rollout | **Local first**, shared-folder support later | Validate local backup PBIX before departmental synced-folder rollout. |
| Update method | **Append new months by default**, **rebuild** available | Default configurable in Settings. Both must be idempotent, correction-safe, and recoverable. |
| Existing active data | Preserve unless explicitly confirmed for removal/replacement | Do not silently drop previously active months during partial updates. |
| Activation | Employee review and explicit confirmation | Confirmation is an operational action, **not** authoritative business approval. |
| Final handoff | Executable + user guide + troubleshooting + maintenance instructions | A successor can run the process and know whom to contact. |

### Append and rebuild: product behavior, not implementation mandate

- **Append (default):** Include newly eligible months while retaining existing active months; do not append duplicate rows on retries. A corrected already-active month must be treated as a **replacement requiring confirmation**, not an extra appended copy.
- **Rebuild (Settings option):** Regenerate the full intended historical dataset from selected current candidate revisions. This need not re-clean raw reports.
- The implementation may use **construct-and-activate a complete snapshot internally for both modes** if this is the simplest safe way to meet the user-facing semantics. Explain that choice and get approval before committing to the architecture.
- If a new selection would remove or replace previously active months or report types, show a precise before/after difference and require explicit confirmation. Preserve a rollback version.

## 3. Rules for Codex and other AI assistants

### Decision authority

**Owner approves each major milestone.** Within an approved milestone, Codex may implement the agreed scope independently, but **must ask before implementing a bug fix**, significant architecture change, scope expansion, or new dependency that materially affects deployment. Codex may investigate, reproduce, test, and explain problems before asking.

**No unapproved feature additions.** Ideas must be recorded in a separate backlog; do not silently convert them into work. No autonomous merge to `main`, deployment, publishing, data deletion, financial-rule changes, Power BI connection edits, or new cloud integration.

### Required proposal before implementation

Every significant proposed change must include:

1. **Employee problem:** Who is affected and what manual work or failure does this solve?
2. **Why now:** Connection to the approved finish line; priority (required / helpful / optional).
3. **Proposed behavior:** What will the employee see and click?
4. **Simpler alternatives:** Including doing nothing or using an existing feature.
5. **Expected effort:** Rough development, testing, and owner-testing time; state uncertainty.
6. **Risks:** Data loss, financial meaning, Windows paths, maintenance, Power BI compatibility, security, permissions.
7. **Acceptance test:** How the owner will know it works.
8. **Approval request:** Stop before implementation if scope or fix is not yet approved.

### Bug-fix protocol

- Reproduce and diagnose without changing code where possible.
- Report root cause, evidence, proposed minimal fix, alternatives, test plan, and risks.
- **Wait for owner approval before changing code**, even if a fix appears straightforward. If urgent, describe urgency rather than silently fixing.
- Once approved, use a feature branch, add regression tests, and report precisely what changed.

### Reporting format after work

Report **what changed**, **why it matters to employees**, **what was tested and where**, **what remains unverified**, **whether any data was written**, **whether main was merged**, **what the owner should do next**, and **what decision requires approval**. Separate synthetic, emulated, hosted CI, and real departmental acceptance evidence.

### Git and testing rules

- Start from latest verified `main`, work on a branch, and keep departmental data out of commits.
- Run relevant automated tests, Windows/Linux CI, and Windows packaging/desktop checks when applicable.
- Never skip or weaken tests to make CI green. A passing test suite is not proof of business accuracy.
- Keep existing candidate revisions, provenance, source hashes, financial schema v2, and disabled authoritative approval/publishing boundaries intact.
- Do not merge or activate a new dataset without explicit owner action and any required repository or departmental approvals.

## 4. Verified baseline and known constraints

### Built and previously tested

- Three report cleaners: CompuClean repairs, CompuClean service orders, TMA work orders.
- Historical year/month folder discovery, legacy XLS/XLSX compatibility, and read-only batch preview.
- Historical batch processing into local immutable, **unapproved** candidate revisions; duplicate detection and correction-review controls.
- Financial schema v2 separates reported values from estimated and legacy arithmetic.
- Windows desktop executable packaging, smoke/restart tests, and GitHub CI on the historical batch-processing feature.
- January–June 2026 preview of 18 report slots; batch candidate outputs were generated and a subsequent reviewed plan showed unchanged selected reports as skipped.

**Not yet confirmed:** Complete, approved historical Power BI dataset generator; backup PBIX compatibility; stable active-output activation; departmental shared-folder operation; handoff on a successor's machine.

### Power BI compatibility findings supplied by owner

Main loaded fact-like tables include `Compuclean list`, `Service_Orders`, `Requests`, and `Work Order`, with supporting `Calendar`, `Equipment`, `Building_Dim`, and `_Measures` tables. The owner clarified that the SharePoint-importing TMA query is **Requests**, while the monthly-table-combining query is **Work Order**. They may overlap but their grains/roles are not yet fully verified.

- Existing repair query combines monthly cleaned tables, derives `Building` from `Location`, normalizes some equipment IDs, and excludes repairs completed on **2026-03-09** and **2026-03-18**. These exclusions require a business explanation before changing them.
- Existing service-order query uses SharePoint monthly paths and transformations; a separate local cleaned CSV query also exists and may be experimental.
- TMA `Requests` uses SharePoint and appends August/September; `Work Order` combines named monthly queries and appends September. Coverage and duplicates must be checked rather than assumed.
- Preserve relationships and DAX in the **backup PBIX** initially. Verify keys, types, and measures before any cutover.
- January–June candidate data is **not** necessarily the complete July–September history referenced by some PBIX queries.

### Known business-data warnings

- March: one unavailable repair reported cost.
- April: two service-order completion dates outside the reporting month.
- May: seven unavailable repair costs; one service-order exclusion; 81 TMA records missing assignments.
- June: seventeen unavailable repair costs; 70 TMA records missing assignments.
- January/February TMA candidate selection or correction state must be checked against the current store.
- Duration defaults, labor rates, reported-versus-estimated financial semantics, and TMA field completeness still require departmental confirmation where relevant.

**Rule:** Preserve missing values and warn. Never silently infer costs, assignments, approvals, or missing months.

## 5. Milestone roadmap and owner approval gates

Each milestone below is a **proposal**, not automatic permission to implement the next one. The current historical generator was already initiated before this governance document; first inspect its actual state and review any new scope before further changes.

### Milestone 1 — Finish historical Power BI snapshot generator (in progress)

**Employee benefit:** Combines selected monthly candidates into predictable historical datasets instead of manual file assembly.

**Deliverables:** Four stable canonical datasets (repairs, service orders, TMA, repair financial summaries), selection/integrity/completeness manifest, clear missing-data warnings, compatibility report, safe local snapshot output. Preserve unapproved status and current candidate history.

**Acceptance:** Generate January–June from selected revisions; compare monthly counts and hashes; check no duplicate revisions; preserve incomplete costs; flag missing selections; regenerate deterministically; do not modify the PBIX or production destinations.

**Gate:** Owner reviews generator output, compatibility gaps, and unresolved TMA/financial mappings before approving PBIX integration.

### Milestone 2 — Connect and validate backup Power BI dashboard

**Employee benefit:** Proves that the cleaned data actually powers the existing visuals without rebuilding the report.

**Work:** Inventory active Power Query sources, relationships, and important DAX dependencies; map new datasets to existing table names and types; test on a **copy** of the PBIX; preserve existing dimensions and measures where possible; compare key visuals/totals and explain differences (including legacy exclusions, partial periods, and financial semantics).

**Acceptance:** Backup PBIX refreshes successfully from the local test snapshot; expected tables and relationships remain valid; selected visuals/measures match documented expectations or have explained differences; no production PBIX or SharePoint changes.

**Gate:** Owner reviews a side-by-side comparison and decides whether the data contract is acceptable. Any cleaner change or model redesign requires a separate proposal.

### Milestone 3 — Employee-guided monthly workflow and update modes

**Employee benefit:** One understandable path from a folder to a refreshed Power BI-ready output.

**Work:** Reduce technical screens for routine use: choose folder → discover/preview → review proposed creates/skips/corrections → process → review completeness → prepare active update. Expose **Append new months** as default and **Rebuild all selected** as a Settings option. Handle existing-month corrections explicitly; show progress, actionable warnings, and a clear success/failure summary. Keep advanced diagnostics available but out of the primary flow.

**Acceptance:** A nonprogrammer can process a new month, retry without duplicates, switch modes in Settings, and understand blocked/partial reports without editing code. Validate corrected-month behavior and no silent loss of existing active months.

**Gate:** Owner approves UI behavior and update semantics after a walkthrough. Do not add unrelated dashboard analytics or approval services.

### Milestone 4 — Stable active Power BI output, safe activation, and shared-folder readiness

**Employee benefit:** Power BI reads one configured location; updates don't require changing query paths.

**Work:** Generate and validate a new complete candidate snapshot, show **before/after month and report-type coverage**, require explicit employee confirmation, activate without leaving mixed old/new files, retain previous active version for rollback, and provide clear status. Start with a local destination. Later assess OneDrive-synced SharePoint folder behavior, ownership, synchronization, and Power BI refresh mechanism before implementation.

**Acceptance:** Backup Power BI refreshes from stable path after activation; an interrupted update leaves prior working data usable; rollback works; partial selection cannot silently remove existing months; warning-only issues are visible; integrity failures block activation. Employee confirmation is not authoritative business approval.

**Gate:** Owner approves activation behavior and separately approves any move to a shared folder or production workflow. **Do not bypass existing publication restrictions**: if activation conflicts with current safeguards, propose a clearly scoped local prototype mode and seek approval before code changes.

### Milestone 5 — Windows release and departmental handoff

**Employee benefit:** Coworkers can use and maintain the application after the owner leaves.

**Work:** Produce installable/portable Windows package appropriate to departmental policy; configure folders without hardcoded personal paths; run on a second/managed computer; create concise employee quick-start, troubleshooting guide, maintainer guide, update/rollback steps, and sample/synthetic test data. Confirm ownership and escalation path.

**Acceptance:** A successor employee can install/launch, configure, process a month, identify warnings, update the backup Power BI input, retry safely, and recover from common errors without Python, Git, or Power BI authoring knowledge. Maintainer can identify version, logs, dependencies, and release procedure.

**Gate:** Owner and designated department contact sign off on handoff readiness. Formal business approval or production publishing may require separate departmental processes.

### Stretch milestone — SharePoint/OneDrive refresh automation (separate approval)

Evaluate **OneDrive-synced read inputs and shared outputs first**; consider direct Microsoft Graph only with IT-approved registration, scopes, and policies. Confirm how the real Power BI environment refreshes (Desktop, Service, gateway, or SharePoint connector). No direct live sign-in or Graph writes without authorization.

**Not part of core handoff unless explicitly promoted by owner.**

## 6. Open decisions and when to resolve them

These are **not blockers to writing this roadmap**; they are checkpoints before the relevant feature ships.

| Decision | Default proposal, not yet approved | Resolve before |
|---|---|---|
| Existing-month correction | Compare old/new month and require explicit replacement confirmation; never double-append | Milestone 3 |
| Activation warning policy | Integrity/schema failures block; business-data warnings allow explicit review and partial selection | Milestone 4 |
| Stable path architecture | Configurable local path with atomic snapshot activation and rollback | Milestone 4 |
| Shared-folder destination | Local-first; test OneDrive synchronization and concurrency before use | Stretch/shared rollout |
| Power BI refresh method | Determine whether Desktop or Service and how stable output is consumed | Milestone 2–4 |
| TMA `Requests` vs `Work Order` | Verify table grain, columns, key uniqueness, relationships and July–September coverage | Milestone 2 |
| March 9/18 repair exclusions | Confirm why old PBIX filters those dates | Milestone 2 |
| Financial warnings and business signoff | Supervisor confirms meanings and acceptable presentation | Before departmental use |
| Successor maintainer | Name owner for software updates and exceptions | Milestone 5 |

## 7. Explicit safeguards and acceptance rules

- **Read vs write:** Discovery/preview should not create candidates; candidate processing should not activate Power BI; activation is a distinct confirmed step.
- **Never mutate raw data.** Keep immutable candidate history, selected revision identity, hashes, and financial-summary binding.
- **Never silently drop history.** Show selected and previously active months/report types, with omissions and replacements before activation.
- **Do not equate clean with correct.** Financial arithmetic matches are not independent business verification.
- **Partial updates:** May include eligible months and exclude others, but exclusions are visible and prior active months remain unless explicitly confirmed otherwise.
- **Failures:** Continue safe processing where appropriate; fail closed on corrupted hashes, incompatible schemas, unsafe paths, or partial active-output replacement.
- **Rollback:** Keep prior active output intact until a complete new version is validated; support a documented rollback.
- **Data privacy:** Keep department files and diagnostics out of GitHub commits and public artifacts; use synthetic samples for tests and screenshots.
- **No hidden deployment:** No automatic SharePoint write, production PBIX edit, authoritative approval, or publishing.

## 8. Testing strategy: demonstrate employee value

For each milestone, test at three levels:

1. **Synthetic automated tests:** Functional rules, idempotency, missing data, schema, path safety, interruption and recovery.
2. **Owner acceptance on Windows:** Real or authorized redacted historical data; actual application UI; screenshots/summary; confirm no unintended writes.
3. **Successor usability test:** Employee unfamiliar with Python/Power BI follows short guide; record confusion, time to completion, and failures.

Keep a compact evidence table in each PR: exact commit, hosted CI link/status, local Windows build, real-data acceptance, known blockers, and explicit owner approval status. **No green status based on unrun checks.**

## 9. Working rhythm and progress register

At the start of each work session, AI should report in plain English:

- Current branch/commit and whether `main` is merged (verify, don't assume).
- Current approved milestone and employee-visible outcome.
- What is already done vs unverified.
- **One recommended next action**, why it matters, approximate time, and what the owner will observe.
- Any decision requiring approval before implementation.

At the end, update this register only with evidence:

| Milestone | Planning status as of 2026-11-12 | Owner acceptance | Merged |
|---|---|---|---|
| Historical discovery, preview and batch processing | Built and tested | Historical batch run and skip-plan checked | Yes, last confirmed `eea5d01` |
| 1. Historical Power BI dataset generator | In progress | Pending | Not confirmed |
| 2. Backup PBIX integration | Not started | Pending | No |
| 3. Guided monthly update UX | Not started as unified workflow | Pending | No |
| 4. Stable active-output activation | Not started | Pending | No |
| 5. Windows handoff | Existing packaging foundations; final handoff pending | Pending | No |
| Stretch: SharePoint automation | Foundations only; authorization pending | Pending | No |

## 10. Reusable AI kickoff prompt

> Read `docs/EQUIPMENT_DATA_MANAGER_MASTER_COMPLETION_ROADMAP.md` before proposing work. Treat owner-confirmed decisions as requirements and open decisions as unresolved. Verify the current Git state. Explain in plain English which **approved milestone** is active, the employee problem it solves, what is already implemented, and what remains. Before writing code, present the proposed change, simpler alternatives, effort, risks, and an acceptance test. **Do not implement new features, bug fixes, architectural changes, or production changes without my approval.** You may investigate and run read-only diagnostics. Do not merge or deploy without explicit permission. Prioritize the simplest reliable guided workflow and maintain existing integrity and financial protections. After implementation, report exact test evidence, unverified items, and one recommended next action. If the task is outside the approved milestone, put it in an optional backlog instead of building it.

## 11. Owner approval record

- **Approved:** Product vision, workflow, stable output goal, local-first rollout, append default/rebuild setting, partial selection with preservation, explicit activation confirmation, successor handoff, and strict AI governance from planning rounds 1–5.
- **Not yet approved:** Detailed implementations of milestones 2–5; activation architecture; exact correction and warning policies; shared-folder/Graph rollout; any new analytics or expanded approval infrastructure.
- **Next review:** Examine the historical snapshot generator's actual outputs and compatibility report, then decide whether to approve the backup PBIX integration milestone.

---

**Success test for the entire project:** A coworker opens the Windows application, selects or refreshes the month folder, reviews the detected changes, processes eligible reports, confirms the Power BI input update, and can refresh the existing dashboard without programming or editing Power Query. The process is repeatable, preserves history, reports issues plainly, and has documented support and recovery steps.
