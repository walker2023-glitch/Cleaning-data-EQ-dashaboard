// Replace only the pilot repair query; do not modify existing production tables.
fnReadMonthlyFolderV2(PilotSnapshot & "/tables/repairs", "repairs", true, {"2026-01", "2026-02"})
