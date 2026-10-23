// Load the three Pilot* queries and fnMonthlyControlTotals first.
let
    Controls = Table.Combine({fnMonthlyControlTotals(PilotRepairs, "repairs"),
        fnMonthlyControlTotals(PilotServiceOrders, "service_orders"),
        fnMonthlyControlTotals(PilotTmaWorkOrders, "tma_work_orders")})
in Controls
