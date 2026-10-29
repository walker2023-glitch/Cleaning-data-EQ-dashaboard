let
    Rows = fnReadMonthlyFolder(PilotSnapshot & "/tables/service_orders", "service_orders", true, {"2026-01", "2026-02"})
in Rows
