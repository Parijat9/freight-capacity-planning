import json
from planning import run
from report import render, comparison_chart

if __name__ == "__main__":
    metrics, plans, scores = run("build")
    chart = comparison_chart(
        "Next-week loads and reservations",
        [p["lane_id"] for p in plans],
        [
            ("Expected loads", [p["expected_loads"] for p in plans]),
            ("Reserved loads", [p["contracted_loads"] for p in plans]),
        ],
    )
    render(
        "build/index.html",
        "Freight capacity planning",
        "Weekly demand, CRM opportunity weighting and a costed contract-versus-spot decision.",
        {
            "Lanes": 6,
            "Test forecast WAPE": f"{metrics['forecast_wape']:.1%}",
            "Interval coverage": f"{metrics['interval_coverage']:.1%}",
            "Scenario cost difference": f"${metrics['scenario_cost_difference_usd']:,.0f}",
        },
        plans,
        "Backtesting holds out 12 weeks after 104 training weeks. The demand generator includes a late regime change on L06. Interval coverage is measured, not guaranteed. Capacity recommendations minimize expected scenario cost under fixed illustrative rates and a 25-load spot limit. The reported difference is against reserving rounded mean demand on the same scenarios, not realized savings.",
        chart=chart,
    )
    print(json.dumps(metrics, indent=2))
