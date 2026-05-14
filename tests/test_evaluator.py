import pytest
from src.evaluator.metrics import MetricsTracker, get_metrics_tracker
from src.evaluator.benchmark import BenchmarkRunner, BenchmarkCase


class TestMetricsTracker:
    def test_record_generation(self):
        tracker = MetricsTracker()
        tracker.record_generation(
            gen_type="sql",
            success=True,
            generation_time_ms=100.0,
            validation_passed=True,
            rag_used=True,
            tokens_used=500,
        )
        summary = tracker.get_summary()
        assert summary["sql"]["total_generations"] == 1
        assert summary["sql"]["successful_generations"] == 1
        assert summary["sql"]["success_rate"] == 1.0
        assert summary["sql"]["avg_generation_time_ms"] == 100.0

    def test_record_multiple(self):
        tracker = MetricsTracker()
        for i in range(10):
            tracker.record_generation(
                gen_type="python",
                success=i < 8,
                generation_time_ms=float(50 + i * 10),
                validation_passed=i < 7,
                rag_used=i < 5,
                tokens_used=300,
            )
        summary = tracker.get_summary()
        assert summary["python"]["total_generations"] == 10
        assert summary["python"]["success_rate"] == 0.8
        assert summary["python"]["validation_pass_rate"] == 0.7

    def test_record_retrieval(self):
        tracker = MetricsTracker()
        for t in [10.0, 20.0, 30.0]:
            tracker.record_retrieval(t)
        summary = tracker.get_summary()
        assert summary["retrieval"]["count"] == 3
        assert summary["retrieval"]["avg_time_ms"] == 20.0

    def test_global_tracker(self):
        tracker = get_metrics_tracker()
        assert isinstance(tracker, MetricsTracker)

    def test_reset(self):
        tracker = MetricsTracker()
        tracker.record_generation("sql", True, 100.0, True, True, 500)
        tracker.reset()
        summary = tracker.get_summary()
        assert summary["sql"]["total_generations"] == 0

    def test_p95_calculation(self):
        tracker = MetricsTracker()
        for i in range(100):
            tracker.record_generation("sql", True, float(i), True, True, 100)
        summary = tracker.get_summary()
        assert summary["sql"]["p95_generation_time_ms"] >= 94.0


class TestBenchmarkRunner:
    async def test_run_with_mock(self):
        runner = BenchmarkRunner(use_mock_llm=True)
        results = await runner.run()
        assert "total_cases" in results
        assert results["total_cases"] > 0
        assert "benchmark_results" in results
        assert len(results["benchmark_results"]) > 0
        for case_result in results["benchmark_results"]:
            assert "case_id" in case_result
            assert "type" in case_result
            assert "generated_code" in case_result
            assert "sandbox_result" in case_result

    async def test_benchmark_case_validation(self):
        runner = BenchmarkRunner(
            cases=[BenchmarkCase(
                id="test_1",
                type="sql",
                requirement="SELECT all from users",
                expected_keywords=["SELECT"],
                table_schema="users(id INT, name VARCHAR)",
            )],
            use_mock_llm=True,
        )
        results = await runner.run()
        assert results["total_cases"] == 1
        assert results["benchmark_results"][0]["case_id"] == "test_1"
