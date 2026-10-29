# Integration Git audit — 2026-10-29

Remote refs were fetched explicitly with
`git fetch origin '+refs/heads/*:refs/remotes/origin/*'` because this checkout's
configured fetch refspec tracked only HEAD. `git ls-remote --symref origin HEAD`
identifies **main** as default. Its head is 06be8633f3816cb43e1039d9547fb4e7c5c91e88.
This is observed Git evidence, independent of inaccessible GitHub PR APIs.

| Remote branch | Exact audited head | Ancestor of integration merge 9d07ced |
|---|---|---|
| `feature/january-rejection-diagnostics` | `631f9c695782a13e2f84ec0eb4e5433ce8371124` | Yes |
| `feature/m0-project-setup` | `288979623af69a41c0af5d7e4fe1f00eb0c070a0` | Yes |
| `feature/m1-cleaning-engine` | `0449dce6217c54ab77c429035f667da70ce9ca16` | Yes |
| `feature/m2-desktop-gui` | `742fd35233f81fdae93070eaa6df95299cdafb80` | Yes |
| `feature/monthly-department-workflow` | `456440d3a078036f681b21e63f23990eb427bdb6` | Yes |
| `feature/multi-month-compatibility` | `e4c4ad210ed41ef49de9257dc81b7e0078d2aad5` | Yes |
| `feature/powerbi-candidate-exports` | `74cb7d3f9cec3b803797ebfc903cc4e4ac05d55e` | Yes |
| `feature/powerbi-integration-pilot` | `68579537df3c175d067ea8ec6a0de12c243ce559` | Yes |
| `feature/powerbi-real-data-readiness` | `ae9a865746a64a3c4a1632c824dd1401b71d949c` | Yes |
| `feature/repair-financial-mapping` | `bffd53fa762fb8f4e24964b762b354db700075aa` | Yes |
| `feature/service-orders-february-layout` | `01237e5b5eb8dae66e34e6109796c22557c9d11d` | Yes |
| `feature/settings-guided-mode` | `25d7a28890bdb3fd48e6fad0a0e3f0884077e980` | Yes |
| `feature/sharepoint-connectivity-foundation` | `14f440172840a52ae7acaa72c78850b5d9956aa6` | Yes |
| `main` | `06be8633f3816cb43e1039d9547fb4e7c5c91e88` | Yes |

No remote feature branch remains independent of the consolidated descendant.
All earlier feature tips form an ancestor chain through 454c7a0, 14f4401 and
owner-created merge ae9a865. Main's M0 merge is on the other parent of 9d07ced.
The merge tree equals ae9a865 exactly; no conflict resolution or duplicated
cherry-picks occurred. Integration-only changes after that merge are documentation,
CI trigger coverage and additional executable-smoke assertions, not cleaner changes.

## PR evidence and bases

Current REST and GraphQL requests fail HTTP 403 Forbidden at the CONNECT proxy
(server envoy). Git read/push access works. API failure cannot establish current
PR state, reviews, branch protections, conflict status or check results. Git's
refs/pull/*/merge are synthetic refs, not proof of approval or mergeability now.
The following bases are the **last recorded** PR metadata, requiring live recheck.
Heads below were independently matched to remote refs/pull/*/head.

| PR | Head branch | Last recorded base | Current evidence |
|---|---|---|---|
| #1 | feature/m0-project-setup | main | Merge commit 06be863 in main confirms inclusion |
| #2 | feature/m1-cleaning-engine | feature/m0-project-setup | Last known open; current state/checks unavailable |
| #3 | feature/m2-desktop-gui | feature/m1-cleaning-engine | Last known open; current state/checks unavailable |
| #4 | feature/service-orders-february-layout | feature/m2-desktop-gui | Last known open; current state/checks unavailable |
| #5 | feature/multi-month-compatibility | feature/service-orders-february-layout | Last known open; current state/checks unavailable |
| #6 | feature/january-rejection-diagnostics | feature/multi-month-compatibility | Last known open; current state/checks unavailable |
| #7 | feature/powerbi-candidate-exports | feature/january-rejection-diagnostics | Last known open; current state/checks unavailable |
| #8 | feature/monthly-department-workflow | feature/powerbi-candidate-exports | Last known open; current state/checks unavailable |
| #9 | feature/settings-guided-mode | feature/monthly-department-workflow | Last known open; current state/checks unavailable |
| #10 | feature/powerbi-integration-pilot | feature/settings-guided-mode | Last known open; current state/checks unavailable |
| #11 | feature/repair-financial-mapping | feature/powerbi-integration-pilot | Last known open; current state/checks unavailable |
| #12 | feature/powerbi-real-data-readiness | feature/repair-financial-mapping | Head advanced to ae9a865; current state/checks unavailable |
| #13 | feature/sharepoint-connectivity-foundation | feature/powerbi-real-data-readiness | Owner merge ae9a865 confirms inclusion into #12 branch |

PRs #1 and #13 have Git merge evidence. For all other PRs, do not infer open/closed
or approved from their continued refs. No PR was merged, closed, retargeted or
approved during integration. Review/close superseded PRs only after final approval
and verified main inclusion; retain branch references until rollback is agreed.

## Local references at audit

The local feature heads matched the audited remote tips except local
feature/powerbi-real-data-readiness, which remained at 454c7a0 (behind remote by
the four foundation commits plus owner merge). No local main branch existed;
origin/main initially pointed to stale fa62100 until the explicit fetch corrected it.
No unique local feature commits were omitted. Working tree was clean before merging.

Backup refs created before integration:

- backup/pre-integration-main-2026-10-29 = 06be8633f3816cb43e1039d9547fb4e7c5c91e88
- backup/pre-integration-sharepoint-2026-10-29 = 14f440172840a52ae7acaa72c78850b5d9956aa6

Integration merge: 9d07ceda09e48eb607bd3bdb6b094d87c3d43b1b.
Parents: main 06be863 and consolidated descendant ae9a865.

## Included pre-documentation commits beyond main

The following list is generated from Git, oldest first, with full identities.
M0 is already reachable from main and is intentionally not replayed.

```text
1718274fedc818d5c5a09511977f18f47b0b7685 Integrate offline CompuClean wrappers and transactional revision processing
5aae099eba7f644f60eee5ef2d776e4b26953f91 Document M1 architecture, validation limits and required fixtures
b98e2e1d817b9d0cb294c43f6001feee903c5a97 Install pinned CI Python through uv on Windows and Linux
7da472f9a574a13ed538ca9c25934563aff6f55e Clarify bootstrap and project Python setup instructions
0449dce6217c54ab77c429035f667da70ce9ca16 Flag cross-period service dates without changing legacy inclusion
56b34834273bdb29d350eae70cfa83ef4360b2ac Add write-free preview, history and desktop workflow boundaries
c13267769de4d0c8fa433193d2ec832319f89fca Build responsive CustomTkinter desktop and Windows packaging checks
4129e4eaf224ebcd9335e88cdf1838ce4583fc9a Document offline desktop preview, validation limits and pilot handoff
742fd35233f81fdae93070eaa6df95299cdafb80 Expose synthetic CI test failures through structured annotations
01237e5b5eb8dae66e34e6109796c22557c9d11d Support observed no-price CompuClean service-order exports
cda87063f12e8eaac985076cc55d268e57c5e18d Validate monthly report metadata and adapt observed TMA XLSX candidates
9e6818df82fd1be9845ed1d6ab98a6293c33fc65 Document compatibility evidence, repair discrepancy and remaining validation gates
e4c4ad210ed41ef49de9257dc81b7e0078d2aad5 Isolate Windows GUI tests in fresh Tcl processes without retries
b90ab202e702c62ec5d4af7a4337e271a8c1b717 Explain CSV period failures and exclusions without changing cleaning rules
91ec2059a4429b4b02af165105430fd8e68ce3f3 Document January reproduction findings and Windows diagnostic workflow
bfeb70f6a128e61c4f1329ab45023783a0d77985 Keep shared errors applicable to adapters without CSV traces
631f9c695782a13e2f84ec0eb4e5433ce8371124 Retain literal CSV date cells separately from pandas missing values
bb387d6964d169796fb49c03e7414db4e41afeed Design normalized candidate contracts and future maintenance review workflow
67dfca4a7218cae8591cd8658af69685ad30d580 Add opt-in normalized candidates through existing cleaners and safe revision stores
1667f27d9c9467e40be50377a408969a51d8a95d Document candidate-only export testing, compatibility and remaining publication gates
b1a4b239fb11da9ee1c8a2331e8407f873743396 Specify complete-snapshot approval selection for future publication
5bbc52efcda4fad4b8f661b2c242828f2472ebb6 Document excluded-record coverage in the classification validation plan
74cb7d3f9cec3b803797ebfc903cc4e4ac05d55e Run Linux GUI CI cases in the tested isolated interpreter harness
5a5748eaab53ae4b77f3211941307f982f25c628 Add local monthly discovery and immutable candidate review packets
ff86ce1e61e690f410203b5e2a1f7a8211854f20 Keep monthly controls readable and Tk finalization on the GUI thread
456440d3a078036f681b21e63f23990eb427bdb6 Document departmental validation and future Graph and Power Query integration
dd73acc55d5ad8fc9c2c4c931b5f5660f32e33fd Add private atomic preferences and safe visual folder settings
0ce760d7fc5a240a7884687beff3ba2aa5c1bab6 Add persistent visual setup and state-aware offline guided help
5d8fc16b046c419498d98c92455c797f7291f33c Document employee setup, guided help maintenance and release checks
d2cc11408502029d352eeb0bd094b554ba1eb267 Clamp tooltip placement for short Windows displays
f5249c16db481385fed9a522a3da9e811e8a1fc1 Preserve synthetic phase diagnostics for Windows executable checks
b22c67eda2a8b3bab8a007d7d37a9401225ae5be Surface packaged smoke phases in check annotations
25d7a28890bdb3fd48e6fad0a0e3f0884077e980 Initialize the restart test window before its self-closing callback
12dd28f7cf9fe0e05106b3c7a8708b190e9c0352 Add isolated multi-month candidate pilot and reconciliation checks
68579537df3c175d067ea8ec6a0de12c243ce559 Document backup-PBIX pilot, compatibility review and finance decisions
2d34c9a9e20905b2d465794472111eb3efc03a5f Separate reported repair totals from estimates in financial schema v2
7ee71ff91da68b6f0b31e8e5f50e42064564ae0d Keep entirely unavailable reported-cost metrics unknown
0e83419478237742004d5ed263f7fe8ed5fc476a Document financial evidence limits, schema-v2 contract and Power BI migration
bffd53fa762fb8f4e24964b762b354db700075aa Explain reported costs and monthly summaries in employee guidance
b343c296735d3ad49e782cd07b2bdc39b6815cad Add four-table Power BI readiness assessment and shared-period queries
454c7a04e24cec16cfdf12d54f74dad247bff555 Document real-data v2 acceptance, model migration and later milestone gates
3bd029114bfe44ef09200ac5cf1a9630d2ed092e Add stable local and synced storage providers for existing processing
4c30c1eccc4341cf66941ebb3a40d3d28f841345 Add injected Graph operations and protected MSAL session foundation
f7bdc129aecfeb57d0c01f1abfcedc8f11bc8323 Respect HTTP header casing for throttling and safe content redirects
14f440172840a52ae7acaa72c78850b5d9956aa6 Explain offline connectivity status and document authorized live-pilot gates
ae9a865746a64a3c4a1632c824dd1401b71d949c Merge pull request #13 from walker2023-glitch/feature/sharepoint-connectivity-foundation
9d07ceda09e48eb607bd3bdb6b094d87c3d43b1b Integrate completed desktop, Power BI v2 and offline SharePoint foundation
```
