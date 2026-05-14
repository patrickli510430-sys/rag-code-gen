from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.evaluator.metrics import MetricsTracker, get_metrics_tracker
from src.llm.python_generator import PythonGenerator
from src.llm.sql_generator import SQLGenerator
from src.llm.providers import MockProvider
from src.validator.python_validator import PythonValidator
from src.validator.sql_validator import SQLValidator
from src.validator.sandbox import CodeSandbox


@dataclass
class BenchmarkCase:
    id: str
    type: str
    requirement: str
    expected_keywords: list[str] = field(default_factory=list)
    table_schema: str = ""
    additional_context: str = ""


DEFAULT_BENCHMARKS: list[BenchmarkCase] = [
    BenchmarkCase(
        id="sql_001",
        type="sql",
        requirement="Get all users who registered in the last 30 days, ordered by registration date",
        expected_keywords=["SELECT", "WHERE", "ORDER BY", ">= CURRENT_DATE - INTERVAL", "30"],
        table_schema="users(id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(200), registered_at TIMESTAMP)",
    ),
    BenchmarkCase(
        id="sql_002",
        type="sql",
        requirement="Count orders grouped by status for the current month",
        expected_keywords=["SELECT", "COUNT", "GROUP BY", "status"],
        table_schema="orders(id INT PRIMARY KEY, user_id INT, status VARCHAR(20), total DECIMAL(10,2), created_at TIMESTAMP)",
    ),
    BenchmarkCase(
        id="sql_003",
        type="sql",
        requirement="Find top 5 products by total sales amount, joining products and order_items",
        expected_keywords=["SELECT", "JOIN", "GROUP BY", "ORDER BY", "LIMIT 5"],
        table_schema="products(id INT PRIMARY KEY, name VARCHAR(200), price DECIMAL(10,2))\norder_items(id INT, order_id INT, product_id INT, quantity INT)",
    ),
    BenchmarkCase(
        id="py_001",
        type="python",
        requirement="Write a function that reads a CSV file and returns the average of a numeric column",
        expected_keywords=["def", "csv", "average", "mean", "return"],
    ),
    BenchmarkCase(
        id="py_002",
        type="python",
        requirement="Write a function to validate email addresses using regex",
        expected_keywords=["def", "re", "import", "return", "True", "False"],
    ),
    BenchmarkCase(
        id="py_003",
        type="python",
        requirement="Write a function that merges two sorted lists into one sorted list without using sorted()",
        expected_keywords=["def", "while", "append", "return"],
    ),
]


class BenchmarkRunner:
    def __init__(
        self,
        cases: list[BenchmarkCase] | None = None,
        tracker: MetricsTracker | None = None,
        use_mock_llm: bool = True,
    ):
        self.cases = cases or DEFAULT_BENCHMARKS
        self.tracker = tracker or get_metrics_tracker()
        self.use_mock_llm = use_mock_llm

        if use_mock_llm:
            mock = MockProvider()
            self.sql_generator = SQLGenerator(provider=mock)
            self.python_generator = PythonGenerator(provider=mock)
        else:
            self.sql_generator = SQLGenerator()
            self.python_generator = PythonGenerator()

        self.sql_validator = SQLValidator()
        self.python_validator = PythonValidator()
        self.sandbox = CodeSandbox()

    async def run(self) -> dict[str, Any]:
        self.tracker.reset()
        results: list[dict[str, Any]] = []

        for case in self.cases:
            result = await self._run_case(case)
            results.append(result)

        summary = self.tracker.get_summary()
        summary["benchmark_results"] = results
        summary["total_cases"] = len(self.cases)
        summary["overall_pass_rate"] = round(
            sum(1 for r in results if r["passed"]) / max(len(results), 1), 4
        )

        return summary

    async def _run_case(self, case: BenchmarkCase) -> dict[str, Any]:
        if case.type == "sql":
            gen_result = await self.sql_generator.generate(
                requirement=case.requirement,
                table_schema=case.table_schema,
                use_rag=False,
            )
            validation = self.sql_validator.validate(gen_result["sql"])
            sandbox_result = self.sandbox.execute_sql(gen_result["sql"])
            generated_code = gen_result["sql"]
        else:
            gen_result = await self.python_generator.generate(
                requirement=case.requirement,
                additional_context=case.additional_context,
                use_rag=False,
            )
            validation = self.python_validator.validate(gen_result["code"])
            sandbox_result = self.sandbox.execute_python(gen_result["code"])
            generated_code = gen_result["code"]

        keyword_match = all(
            kw.lower() in generated_code.lower()
            for kw in case.expected_keywords
        )

        passed = validation.is_valid and validation.is_safe and keyword_match

        self.tracker.record_generation(
            gen_type=case.type,
            success=gen_result.get("raw_response") is not None,
            generation_time_ms=gen_result["generation_time_ms"],
            validation_passed=validation.is_valid and validation.is_safe,
            rag_used=gen_result["context_used"],
            tokens_used=gen_result["usage"].get("total_tokens", 0),
        )

        return {
            "case_id": case.id,
            "type": case.type,
            "passed": passed,
            "generated_code": generated_code,
            "validation": {
                "is_valid": validation.is_valid,
                "is_safe": validation.is_safe,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            "sandbox_result": {
                "success": sandbox_result.success,
                "output": sandbox_result.output,
                "error": sandbox_result.error,
            },
            "keyword_match": keyword_match,
            "generation_time_ms": gen_result["generation_time_ms"],
            "tokens_used": gen_result["usage"].get("total_tokens", 0),
        }

    def save_results(self, results: dict[str, Any], path: str = "benchmark_results.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)


async def run_benchmark_cli():
    runner = BenchmarkRunner(use_mock_llm=True)
    results = await runner.run()
    runner.save_results(results)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run_benchmark_cli())
