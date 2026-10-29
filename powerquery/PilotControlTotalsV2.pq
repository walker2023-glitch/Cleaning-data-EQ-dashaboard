let
    Controls = Table.Combine({fnMonthlyControlTotalsV2(PilotRepairsV2, "repairs"),
        fnMonthlyControlTotalsV2(PilotServiceOrders, "service_orders"),
        fnMonthlyControlTotalsV2(PilotTmaWorkOrders, "tma_work_orders")})
in Controls
