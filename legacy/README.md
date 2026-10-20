# Uploaded source reference

`clean/` contains the six user-uploaded files, byte for byte. SHA-256 hashes are
recorded in `source_hashes.json` and checked by tests. This is provenance of the
uploads, not independent verification of their business correctness or origin.

These are reference inputs for discovery, **not** production adapters. They are
excluded from the installed application wheel. Do not run their `main()` or
`process_file()` functions against real data: they use fixed local paths and
can write or overwrite CSVs. Tests import only the three pure DataFrame cleaner
functions via pytest's `legacy` import path and use synthetic data.

`list_clean.py` imports missing `dashboard.taxonomy`; do not add guessed
replacement functions or treat inventory as a transaction report. Its original
helper module and optional lookup fixture are needed only if inventory is scoped
into a later milestone. See `docs/discovery.md` for source findings and risks.
