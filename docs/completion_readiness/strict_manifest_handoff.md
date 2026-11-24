# Strict manifest validation — review handoff

Owner-approved narrow fix, separate branch `feature/strict-manifest-metadata`,
commit `6ab7a804b9be71b3cf115968b2332071b29ee346`, based on main b23a5e6.
No schema change, generated data change or activation implementation.

- Comparison V1/V2/V3: compare canonical JSON representations of parsed/recomputed
  metadata. Exact flags and all nested numeric/count representations remain distinct;
  dictionary key order/whitespace remain compatible.
- Canonical: explicit existing Boolean fields and integer/nullable-integer row/month/
  diagnostic counts. Do not coerce Boolean numbers; preserve legitimate nulls.
- Two earlier independent analyzer regressions now require application rejection too.
  102 additional cases cover valid/reordered manifests, malformed flags/counts,
  equal-valued integral floats, warning/lineage counts and retained canonical metadata.
- No cleaning, financial, classification, Settings, monthly update, Power Query,
  dependency or existing export-generation behavior was changed. Existing CI only
  gained this branch in packaging/acceptance push gates.

Executed: **408 focused tests passed**; full suite **1,357 passed**, zero failures,
errors or skips (1,274 core + 83 isolated real-widget cases). Source distribution,
wheel and native Linux PyInstaller builds passed; every application Python/Markdown
file in the wheel matches source. Source/wheel/frozen phase-55 desktop smokes and
fresh-process restart passed. Synthetic acceptance: **53 PASS, 8 REVIEW, 0 FAIL,
4 NOT TESTED**; clean application Git provenance. Existing font fallback warnings
are environmental; actual Power BI/employee/DPI/business acceptance is separate.

Hosted checks at the exact fix head:

- [Windows/Linux regression and native Windows packaging](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/actions/runs/45411388265).
- [Windows/Linux synthetic acceptance](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/actions/runs/45411388016): **Success**, 12m 22s; native Windows build, full selected-app regression, source/frozen smoke and restart passed.

Final statuses are recorded in the delivery; no hosted success is inferred from
local checks. The proposed 3b Windows failure matrix is not implemented or claimed
executed. No activation service, state file or wrapper was added.

Draft creation returned `Post "https://api.github.com/graphql": Forbidden`.
[Exact fix comparison / create PR](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/compare/main...feature/strict-manifest-metadata?expand=1).
Do not merge automatically. Review/merge this prerequisite separately before a
later owner-approved 3b implementation branch starts from verified new main.
