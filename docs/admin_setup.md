# Administration preparation (no live integration in M0)

`config.example.toml` contains empty placeholders only. Copy it to ignored
`config.local.toml` for later approved non-secret IDs. M0 validates table shape
and offline mode; it does not validate tenant IDs, authority, scopes, folder
existence, consent, or permissions. Unknown keys (including secret fields) fail
configuration validation, and errors do not echo values. Populating IDs cannot
enable network access. There is no authentication implementation or token cache.

Before any connected milestone, IT must approve an Entra public/native client registration, tenant
restrictions, redirect URI, delegated permissions/site grants, secure Windows
token caching and sign-out behavior. Confirm each user's independent SharePoint
permissions. Do not assume broad permissions or a specific selected-site grant
will work without approval and testing. Do not create/embed a client secret.

Collect the exact site, drive and approved test folder identifiers through an
authorized process. The template's raw/cleaned/log IDs are placeholders for roots;
per-report mappings still need discovery and later configuration design. No
tenant URL, Graph scope or production folder is guessed. Use separate approved
test locations when integration tests are eventually implemented.

Windows managed-PC packaging, signing, MFA/conditional access testing, recovery,
retention and operator coordination are later milestones described in `design.md`.
No production SharePoint data or Power BI files are accessed or changed in M0.


The local departmental workflow uses a separate `workspace.example.toml` template,
not the inert Microsoft settings. See `monthly_workflow.md` for separate raw,
candidate and reserved approved roots; no approved files are written. The full
future registration/permissions/cache/concurrency checklist is in
`sharepoint_integration_plan.md`. Local sync availability is not Graph integration
or evidence of cloud synchronization.
