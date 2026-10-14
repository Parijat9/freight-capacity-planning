"""Forecast committed loads, then reserve capacity against demand scenarios."""

import csv
import json
import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent


def solve(matrix, vector):
    a = [list(row) + [value] for row, value in zip(matrix, vector)]
    n = len(vector)
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        if abs(a[i][i]) < 1e-10:
            raise ValueError("Singular design")
        scale = a[i][i]
        a[i] = [v / scale for v in a[i]]
        for j in range(n):
            if j != i:
                scale = a[j][i]
                a[j] = [v - scale * w for v, w in zip(a[j], a[i])]
    return [row[-1] for row in a]


def features(t):
    return [1, t / 52, math.sin(2 * math.pi * t / 52), math.cos(2 * math.pi * t / 52)]


def forecast(history, horizon, method="seasonal_trend"):
    if len(history) < 52 or horizon < 1:
        raise ValueError("Need 52 observed weeks and a positive horizon")
    if any(not math.isfinite(v) or v < 0 for v in history):
        raise ValueError("Invalid historical demand")
    if method == "last_four_mean":
        return [sum(history[-4:]) / 4] * horizon
    if method == "seasonal_naive":
        return [history[len(history) - 52 + (h % 52)] for h in range(horizon)]
    if method != "seasonal_trend":
        raise ValueError("Unknown model")
    x = [features(i) for i in range(len(history))]
    beta = solve(
        [[sum(row[i] * row[j] for row in x) for j in range(4)] for i in range(4)],
        [sum(row[i] * y for row, y in zip(x, history)) for i in range(4)],
    )
    return [
        max(0, sum(b * f for b, f in zip(beta, features(t))))
        for t in range(len(history), len(history) + horizon)
    ]


def wape(actual, predicted):
    if len(actual) != len(predicted) or not actual:
        raise ValueError("Aligned nonempty series required")
    denominator = sum(abs(x) for x in actual)
    return (
        sum(abs(a - p) for a, p in zip(actual, predicted)) / denominator
        if denominator
        else None
    )


def calibration_errors(history):
    return [
        history[t] - forecast(history[:t], 1)[0]
        for t in range(max(52, len(history) - 24), len(history))
    ]


def interval_radius(errors, coverage=0.9):
    if not errors or not 0 < coverage < 1:
        raise ValueError("Invalid calibration")
    values = sorted(abs(e) for e in errors)
    return values[min(len(values) - 1, math.ceil((len(values) + 1) * coverage) - 1)]


def cost(
    demand,
    contracted,
    contract_rate=820,
    spot_rate=1100,
    shortfall_penalty=1900,
    spot_limit=25,
):
    if (
        min(demand, contracted, contract_rate, spot_rate, shortfall_penalty, spot_limit)
        < 0
    ):
        raise ValueError("Negative planning input")
    deficit = max(0, demand - contracted)
    spot = min(deficit, spot_limit) if spot_rate < shortfall_penalty else 0
    unmet = deficit - spot
    return (
        contracted * contract_rate + spot * spot_rate + unmet * shortfall_penalty,
        spot,
        unmet,
    )


def choose_capacity(scenarios):
    if not scenarios:
        raise ValueError("Demand scenarios required")
    candidates = range(math.ceil(max(scenarios)) + 1)
    scored = [
        (sum(cost(d, c)[0] for d in scenarios) / len(scenarios), c) for c in candidates
    ]
    expected, selected = min(scored)
    return selected, expected


def generate():
    rng = random.Random(73)
    rows = []
    for lane in range(1, 7):
        for week in range(116):
            trend = 0.22 * week if lane < 5 else -0.04 * week
            seasonal = (8 + lane) * math.sin(2 * math.pi * week / 52)
            shock = 14 if lane == 6 and week >= 104 else 0
            loads = max(
                0,
                round(
                    35
                    + lane * 9
                    + trend
                    + seasonal
                    + rng.gauss(0, 3 + lane / 2)
                    + shock
                ),
            )
            rows.append(
                {
                    "lane_id": f"L{lane:02}",
                    "week": week,
                    "week_start": str(date(2024, 7, 1) + timedelta(weeks=week)),
                    "booked_loads": loads,
                }
            )
    return rows


def pipeline_deals():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE deal(deal_id TEXT PRIMARY KEY,lane_id TEXT,snapshot_stage TEXT,snapshot_on TEXT,closed_on TEXT,outcome TEXT,weekly_loads INTEGER,already_booked INTEGER)"
    )
    rng = random.Random(101)
    stages = ["qualified", "proposal", "negotiation"]
    for i in range(240):
        stage = stages[i % 3]
        won = rng.random() < [0.25, 0.5, 0.75][i % 3]
        db.execute(
            "INSERT INTO deal VALUES(?,?,?,?,?,?,?,?)",
            (
                f"D{i:04}",
                f"L{i%6+1:02}",
                stage,
                "2026-03-01",
                "2026-04-30",
                "won" if won else "lost",
                rng.randint(1, 5),
                int(won),
            ),
        )
    for i in range(24):
        db.execute(
            "INSERT INTO deal VALUES(?,?,?,?,?,?,?,?)",
            (
                f"O{i:04}",
                f"L{i%6+1:02}",
                stages[i % 3],
                "2026-09-01",
                None,
                None,
                rng.randint(1, 5),
                0,
            ),
        )
    return db


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = generate()
    write_csv(out / "weekly_demand.csv", rows)
    db = pipeline_deals()
    crm = [
        dict(r)
        for r in db.execute(
            (HERE / "sql/crm_pipeline.sql").read_text(), {"cutoff": "2026-09-20"}
        )
    ]
    write_csv(out / "crm_pipeline.csv", crm)
    db.close()
    scores = []
    plans = []
    details = []
    # 104 weeks train, 12 untouched test. All methods forecast the same 12-week horizon.
    for lane in sorted({r["lane_id"] for r in rows}):
        history = [r["booked_loads"] for r in rows if r["lane_id"] == lane]
        train, test = history[:104], history[104:]
        errors = calibration_errors(train)
        radius = interval_radius(errors)
        for method in ["last_four_mean", "seasonal_naive", "seasonal_trend"]:
            pred = forecast(train, 12, method)
            scores.append(
                {
                    "lane_id": lane,
                    "method": method,
                    "wape": wape(test, pred),
                    "test_weeks": 12,
                }
            )
        pred = forecast(train, 12)
        for i, (actual, estimate) in enumerate(zip(test, pred)):
            details.append(
                {
                    "lane_id": lane,
                    "week": 104 + i,
                    "actual": actual,
                    "forecast": round(estimate, 2),
                    "lower": round(max(0, estimate - radius), 2),
                    "upper": round(estimate + radius, 2),
                    "covered": int(abs(actual - estimate) <= radius),
                }
            )
        # Plan after all 116 observed weeks; held-out scores above are never used to fit this model.
        future = forecast(history, 1)[0]
        incremental = next(
            r["expected_incremental_loads"] for r in crm if r["lane_id"] == lane
        )
        demand = future + incremental
        residuals = calibration_errors(history)
        scenarios = [max(0, round(demand + e)) for e in residuals]
        selected, expected_cost = choose_capacity(scenarios)
        baseline = math.ceil(demand)
        basecost = sum(cost(d, baseline)[0] for d in scenarios) / len(scenarios)
        plans.append(
            {
                "lane_id": lane,
                "booked_forecast": round(future, 2),
                "crm_incremental": round(incremental, 2),
                "expected_loads": round(demand, 2),
                "contracted_loads": selected,
                "mean_spot_loads": round(
                    sum(cost(d, selected)[1] for d in scenarios) / len(scenarios), 2
                ),
                "mean_unmet_loads": round(
                    sum(cost(d, selected)[2] for d in scenarios) / len(scenarios), 2
                ),
                "expected_cost_usd": round(expected_cost, 2),
                "ceil_demand_cost_usd": round(basecost, 2),
            }
        )
    write_csv(out / "backtest_scores.csv", scores)
    write_csv(out / "forecast_detail.csv", details)
    write_csv(out / "capacity_plan.csv", plans)
    model = [r for r in scores if r["method"] == "seasonal_trend"]
    metrics = {
        "data": "synthetic",
        "train_weeks": 104,
        "test_weeks": 12,
        "lanes": 6,
        "forecast_wape": wape(
            [r["actual"] for r in details], [r["forecast"] for r in details]
        ),
        "interval_coverage": sum(r["covered"] for r in details) / len(details),
        "expected_weekly_cost_usd": round(
            sum(r["expected_cost_usd"] for r in plans), 2
        ),
        "scenario_cost_difference_usd": round(
            sum(r["ceil_demand_cost_usd"] - r["expected_cost_usd"] for r in plans), 2
        ),
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics, plans, scores
