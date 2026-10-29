let
    Rows = fnReadMonthlyFolder(PilotSnapshot & "/tables/tma_work_orders", "tma_work_orders", true, {"2026-01", "2026-02"})
in Rows
