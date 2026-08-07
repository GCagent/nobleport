import asyncio
import unittest

from api.nano_optimizer import ContextItem, ExecutionLane, NanoOptimizer, run_parallel


class NanoOptimizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.optimizer = NanoOptimizer(target_context_chars=120)

    def test_fast_lane(self):
        lane, _, approval = self.optimizer.classify_lane("extract the project id")
        self.assertEqual(lane, ExecutionLane.FAST)
        self.assertFalse(approval)

    def test_financial_action_is_gated(self):
        lane, _, approval = self.optimizer.classify_lane("release funds to the subcontractor")
        self.assertEqual(lane, ExecutionLane.GATED)
        self.assertTrue(approval)

    def test_mandatory_context_is_never_pruned_for_budget(self):
        items = [
            ContextItem("governance", "G" * 150, relevance=1.0, mandatory=True),
            ContextItem("noise", "N" * 100, relevance=100.0),
        ]
        selected = self.optimizer.select_context(items)
        self.assertEqual([i.key for i in selected], ["governance"])

    def test_relevant_small_context_wins_budget(self):
        items = [
            ContextItem("a", "A" * 60, relevance=10.0),
            ContextItem("b", "B" * 60, relevance=1.0),
            ContextItem("c", "C" * 60, relevance=9.0),
        ]
        selected = self.optimizer.select_context(items)
        self.assertEqual({i.key for i in selected}, {"a", "c"})

    def test_plan_reports_reduction(self):
        items = [
            ContextItem("required", "R" * 20, relevance=1.0, mandatory=True),
            ContextItem("useful", "U" * 80, relevance=10.0),
            ContextItem("noise", "N" * 200, relevance=0.1),
        ]
        plan = self.optimizer.plan("summarize status", items)
        self.assertEqual(plan.selected_chars, 100)
        self.assertAlmostEqual(plan.reduction_pct, 66.67, places=2)


class ParallelTests(unittest.IsolatedAsyncioTestCase):
    async def test_independent_reads_run_in_parallel(self):
        async def slow(value):
            await asyncio.sleep(0.03)
            return value

        results = await run_parallel(
            {
                "rag": lambda: slow("context"),
                "crm": lambda: slow("lead"),
            },
            timeout_s=0.2,
        )
        self.assertEqual(results["rag"], "context")
        self.assertEqual(results["crm"], "lead")

    async def test_timeout_is_isolated(self):
        async def slow():
            await asyncio.sleep(0.1)
            return "late"

        async def fast():
            return "ok"

        results = await run_parallel(
            {"slow": slow, "fast": fast},
            timeout_s=0.01,
        )
        self.assertIsInstance(results["slow"], Exception)
        self.assertEqual(results["fast"], "ok")


if __name__ == "__main__":
    unittest.main()
