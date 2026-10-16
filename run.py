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
        "Estimate next week’s loads and compare the cost of reserving capacity with booking extra capacity later.",
        {
            "Lanes": 6,
            "Forecast error (WAPE)": f"{metrics['forecast_wape']:.1%}",
            "Weeks within forecast range": f"{metrics['interval_coverage']:.1%}",
            "Sample cost difference": f"${metrics['scenario_cost_difference_usd']:,.0f}",
        },
        plans,
        "The forecast uses 104 weeks of sample history and is checked against the next 12 weeks. One route changes demand sharply near the end. Forecast error is the total absolute error divided by total actual loads (WAPE). The forecast range aims to cover 90% of weeks; the measured result is shown above. The plan compares sample costs with a limit of 25 extra loads. The cost difference is against reserving average demand, not savings achieved in a business.",
        chart=chart,
    )
    print(json.dumps(metrics, indent=2))
