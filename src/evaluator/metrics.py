from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HISTORY_FILE = Path(__file__).parent.parent.parent / "metrics_history.json"


@dataclass
class GenerationMetrics:
    total_generations: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    generation_times_ms: list[float] = field(default_factory=list)
    validation_pass_count: int = 0
    validation_fail_count: int = 0
    rag_used_count: int = 0
    rag_not_used_count: int = 0
    total_tokens_used: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_generations == 0:
            return 0.0
        return self.successful_generations / self.total_generations

    @property
    def avg_generation_time_ms(self) -> float:
        if not self.generation_times_ms:
            return 0.0
        return statistics.mean(self.generation_times_ms)

    @property
    def median_generation_time_ms(self) -> float:
        if not self.generation_times_ms:
            return 0.0
        return statistics.median(self.generation_times_ms)

    @property
    def p95_generation_time_ms(self) -> float:
        if not self.generation_times_ms:
            return 0.0
        sorted_times = sorted(self.generation_times_ms)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def validation_pass_rate(self) -> float:
        total = self.validation_pass_count + self.validation_fail_count
        if total == 0:
            return 0.0
        return self.validation_pass_count / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_generations": self.total_generations,
            "successful_generations": self.successful_generations,
            "failed_generations": self.failed_generations,
            "success_rate": round(self.success_rate, 4),
            "avg_generation_time_ms": round(self.avg_generation_time_ms, 2),
            "median_generation_time_ms": round(self.median_generation_time_ms, 2),
            "p95_generation_time_ms": round(self.p95_generation_time_ms, 2),
            "validation_pass_rate": round(self.validation_pass_rate, 4),
            "rag_used_count": self.rag_used_count,
            "rag_not_used_count": self.rag_not_used_count,
            "total_tokens_used": self.total_tokens_used,
        }


class MetricsTracker:
    def __init__(self):
        self._sql_metrics = GenerationMetrics()
        self._python_metrics = GenerationMetrics()
        self._retrieval_times_ms: list[float] = []
        self._generation_history: list[dict[str, Any]] = []
        self._load_from_disk()

    def _load_from_disk(self):
        """Restore history from persisted JSON file."""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                history = data.get("history", [])
                self._generation_history = history
                # Rebuild aggregate counters from history
                for entry in history:
                    gen_type = entry.get("type", "sql")
                    metrics = self._sql_metrics if gen_type == "sql" else self._python_metrics
                    metrics.total_generations += 1
                    if entry.get("success"):
                        metrics.successful_generations += 1
                    else:
                        metrics.failed_generations += 1
                    metrics.generation_times_ms.append(entry.get("generation_time_ms", 0))
                    if entry.get("validation_passed"):
                        metrics.validation_pass_count += 1
                    else:
                        metrics.validation_fail_count += 1
                    if entry.get("rag_used"):
                        metrics.rag_used_count += 1
                    else:
                        metrics.rag_not_used_count += 1
                    metrics.total_tokens_used += entry.get("tokens_used", 0)
        except Exception:
            self._generation_history = []

    def _save_to_disk(self):
        """Persist history to JSON file."""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "history": self._generation_history[-500:],  # Keep last 500
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_generation(
        self,
        gen_type: str,
        success: bool,
        generation_time_ms: float,
        validation_passed: bool,
        rag_used: bool,
        tokens_used: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        metrics = self._sql_metrics if gen_type == "sql" else self._python_metrics
        metrics.total_generations += 1
        if success:
            metrics.successful_generations += 1
        else:
            metrics.failed_generations += 1
        metrics.generation_times_ms.append(generation_time_ms)
        if validation_passed:
            metrics.validation_pass_count += 1
        else:
            metrics.validation_fail_count += 1
        if rag_used:
            metrics.rag_used_count += 1
        else:
            metrics.rag_not_used_count += 1
        metrics.total_tokens_used += tokens_used

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": gen_type,
            "success": success,
            "generation_time_ms": generation_time_ms,
            "validation_passed": validation_passed,
            "rag_used": rag_used,
            "tokens_used": tokens_used,
            "metadata": metadata or {},
        }
        self._generation_history.append(entry)
        self._save_to_disk()

    def record_retrieval(self, retrieval_time_ms: float):
        self._retrieval_times_ms.append(retrieval_time_ms)

    def get_summary(self) -> dict[str, Any]:
        return {
            "sql": self._sql_metrics.to_dict(),
            "python": self._python_metrics.to_dict(),
            "retrieval": {
                "count": len(self._retrieval_times_ms),
                "avg_time_ms": round(statistics.mean(self._retrieval_times_ms), 2) if self._retrieval_times_ms else 0,
                "median_time_ms": round(statistics.median(self._retrieval_times_ms), 2) if self._retrieval_times_ms else 0,
            },
            "total_tokens_used": self._sql_metrics.total_tokens_used + self._python_metrics.total_tokens_used,
        }

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent history entries, newest first."""
        return list(reversed(self._generation_history[-limit:]))

    def reset(self):
        self._sql_metrics = GenerationMetrics()
        self._python_metrics = GenerationMetrics()
        self._retrieval_times_ms = []
        self._generation_history = []
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()


_global_tracker = MetricsTracker()


def get_metrics_tracker() -> MetricsTracker:
    return _global_tracker
