// Create a text parameter PilotSnapshot pointing at the exact .../pilot/snapshot.
// Load fnReadMonthlyFolder first. ONLY in a new or backup review PBIX.
let
    Rows = fnReadMonthlyFolder(PilotSnapshot & "/tables/repairs", "repairs", true, {"2026-01", "2026-02"})
in Rows
