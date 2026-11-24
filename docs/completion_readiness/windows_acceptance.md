# Windows employee acceptance — Milestone 3a

Use only invented reports, a new private candidate store and a backup/blank PBIX.
Use the reviewed 3a Windows artifact from
[the exact-head packaging run](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/actions/runs/45231387857),
or build the verified revision using [Windows packaging](../windows_packaging.md).
Match the executable/release evidence to the reviewed revision; do not reuse an
unidentified Downloads prototype. Managed-PC acceptance is still owner-pending.

Record tester, date, Windows/build version, executable digest/revision, display
scaling, chosen local layout and pass/fail/evidence for each item. Keep reports private.

- [ ] Launch, configure Raw Data/local candidates/reserved-approved in Settings,
  Check Locations and Save Settings. No network/synced/production output root.
- [ ] Use **Process Multiple Months → Batch processing** to process invented January.
  Open **Power BI snapshot**, whose primary panel is **Monthly Historical Update**.
- [ ] **Initial build (no baseline)** → **Choose new local output location** →
  **Review monthly update**. See Rebuild History explicitly labeled initial build.
  Read complete coverage/counts/warnings before confirming. Reject the final dialog:
  verify no new output. Confirm a fresh review and verify a completed `snapshot`.
- [ ] Process February. **Choose completed baseline** (January), January–February
  range, new destination, Review monthly update. See **Add New Months**; verify
  January selections/counts unchanged and February included once. Confirm/save.
- [ ] Explicitly select that new output as baseline and another new destination:
  **No Update Needed**, generation disabled, no duplicate output.
- [ ] Change one invented January source: **Review Required**. Complete its existing
  single-report correction approval AND **Process Reports & Save Candidate**.
  Re-review: **Rebuild History**, exact replacement shown. Separate replacement
  consent plus final confirmation required. All prior revisions/outputs remain.
- [ ] Select a smaller range: **Review Required**; Add unavailable. Rebuild requires
  explicit displayed removal consent. Alternatively expand range to retain history.
- [ ] Missing report/candidate, ambiguous files or invalid/missing baseline: month/type
  and next action shown, generation blocked. Never interpret missing as zero rows.
- [ ] Change evidence after review: generation rejects stale confirmation, no completed
  partial output. Restore evidence and review again; do not edit manifests to force it.
- [ ] Stop a longer generation: prior outputs remain; no completed partial output.
  Never import `.s`; after abrupt termination preserve it for diagnosis, then use a
  fresh destination. No automatic deletion/resume of another run.
- [ ] Restart: Settings/candidate history survive, old confirmation does not. Explicitly
  choose baseline/destination and review again. Check Settings → Processing History.
- [ ] Test tab/keyboard/F1 help, readable plan and warnings, checkbox focus, scrolling,
  intended DPI settings, accessibility policy and first-time employee comprehension.
- [ ] If using backup Power BI, validate the exact selected canonical/V3 bundle with
  Python and the independent analyzer first. Import disconnected comparison tables;
  preserve existing relationships/DAX. Follow [mapping and blockers](power_bi_audit.md).

For an automated executable check, use a NEW disposable smoke directory:

```powershell
$dir = Join-Path $PWD 'data/acceptance-new-run'
$p = Start-Process '.\dist\EquipmentDataManager\EquipmentDataManager.exe' -ArgumentList @('--smoke-test','--smoke-dir',$dir) -PassThru
if (-not $p.WaitForExit(180000)) { $p.Kill(); throw 'Smoke timeout' }
if ($p.ExitCode -ne 0) { throw 'Smoke failed' }
Get-Content "$dir/desktop-smoke.json"
Get-Content "$dir/restore-smoke.json"
```

Require `status: passed`, **phase 55**, and restore `passed: true`. These results do
not establish business accuracy or actual Power BI execution. Record exceptions
and owner disposition; do not claim sign-off merely because CI is green.
