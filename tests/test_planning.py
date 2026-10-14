import io
import json
import unittest
from pathlib import Path
from planning import *
from crm import fetch_deals


class Planning(unittest.TestCase):
    def test_linear_forecast(self):
        pred = forecast([20 + 0.2 * t for t in range(104)], 12)
        self.assertAlmostEqual(pred[0], 40.8, places=6)

    def test_zero_denominator(self):
        self.assertIsNone(wape([0, 0], [1, 1]))

    def test_alignment_rejected(self):
        with self.assertRaises(ValueError):
            wape([1], [1, 2])

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            forecast([-1] * 60, 1)

    def test_holdout_cannot_affect_training(self):
        data = [r["booked_loads"] for r in generate() if r["lane_id"] == "L01"]
        pred = forecast(data[:104], 12)
        data[104:] = [999] * 12
        self.assertEqual(pred, forecast(data[:104], 12))

    def test_scenario_choice_is_minimum(self):
        scenarios = [30, 35, 40, 50]
        c, expected = choose_capacity(scenarios)
        for candidate in range(60):
            self.assertLessEqual(
                expected, sum(cost(d, candidate)[0] for d in scenarios) / 4 + 1e-8
            )

    def test_spot_limit_and_shortfall(self):
        amount, spot, unmet = cost(100, 50)
        self.assertEqual((spot, unmet), (25, 25))
        self.assertEqual(amount, 50 * 820 + 25 * 1100 + 25 * 1900)

    def test_cheap_shortfall_not_expensive_spot(self):
        self.assertEqual(cost(10, 0, spot_rate=2000, shortfall_penalty=1000)[1], 0)

    def test_empty_scenarios_rejected(self):
        with self.assertRaises(ValueError):
            choose_capacity([])

    def test_future_outcome_not_leaked(self):
        db = pipeline_deals()
        sql = (HERE / "sql/crm_pipeline.sql").read_text()
        before = [dict(r) for r in db.execute(sql, {"cutoff": "2026-09-20"})]
        db.execute(
            "UPDATE deal SET closed_on='2027-01-01',outcome='won' WHERE deal_id LIKE 'O%'"
        )
        after = [dict(r) for r in db.execute(sql, {"cutoff": "2026-09-20"})]
        self.assertEqual(before, after)
        db.close()

    def test_crm_pagination(self):
        calls = []

        class Response(io.BytesIO):
            status = 200

        def opener(request, timeout):
            calls.append(request.full_url)
            n = len(calls)
            return Response(
                json.dumps(
                    {"data": [{"id": str(n)}], "info": {"more_records": n == 1}}
                ).encode()
            )

        self.assertEqual(len(fetch_deals("test", opener=opener)), 2)
        self.assertIn("page=2", calls[1])

    def test_crm_domain_restricted(self):
        with self.assertRaises(ValueError):
            fetch_deals("test", "https://example.com")


if __name__ == "__main__":
    unittest.main()
