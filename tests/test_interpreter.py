"""Tests for metrics interpretation."""

import json
import os
import tempfile

import pytest

from src.interpreter import MetricsParseError, interpret, load_metrics
from src.models import MetricsSummary, SLO


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestLoadMetrics:
    def test_load_passing_json(self):
        path = os.path.join(FIXTURES_DIR, "metrics-passing.json")
        metrics, warnings = load_metrics(path)
        assert metrics.p95_ms == 350.0
        assert metrics.error_rate == 0.005
        assert metrics.throughput_rps == 195.0

    def test_load_failing_json(self):
        path = os.path.join(FIXTURES_DIR, "metrics-failing.json")
        metrics, warnings = load_metrics(path)
        assert metrics.p95_ms == 900.0
        assert metrics.error_rate == 0.05
        assert metrics.cpu_percent == 92.0

    def test_load_csv(self):
        path = os.path.join(FIXTURES_DIR, "metrics-partial.csv")
        metrics, warnings = load_metrics(path)
        assert metrics.p50_ms == 130.0
        assert metrics.p95_ms == 380.0
        assert metrics.error_rate == 0.008
        # Missing fields produce warnings
        assert any("p90_ms" in w for w in warnings)
        assert any("p99_ms" in w for w in warnings)

    def test_missing_file(self):
        with pytest.raises(MetricsParseError, match="not found"):
            load_metrics("/nonexistent/metrics.json")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(b"<metrics/>")
            f.flush()
            try:
                with pytest.raises(MetricsParseError, match="unsupported"):
                    load_metrics(f.name)
            finally:
                os.unlink(f.name)

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("{bad}")
            f.flush()
            try:
                with pytest.raises(MetricsParseError, match="parse"):
                    load_metrics(f.name)
            finally:
                os.unlink(f.name)

    def test_non_object_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump([1, 2], f)
            f.flush()
            try:
                with pytest.raises(MetricsParseError, match="object"):
                    load_metrics(f.name)
            finally:
                os.unlink(f.name)

    def test_empty_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("p50_ms,p95_ms\n")  # header only
            f.flush()
            try:
                with pytest.raises(MetricsParseError, match="no data"):
                    load_metrics(f.name)
            finally:
                os.unlink(f.name)


class TestInterpret:
    def _default_slo(self):
        return SLO(latency_ms={"p95": 400, "p99": 800}, error_rate=0.01)

    def test_passing_metrics(self):
        metrics = MetricsSummary(
            p95_ms=350, p99_ms=700, error_rate=0.005,
            throughput_rps=195, cpu_percent=55, memory_percent=62,
        )
        result = interpret(metrics, self._default_slo())
        assert result.status == "pass"
        assert all(c["result"] == "pass" for c in result.checks)
        assert len(result.risks) == 0

    def test_failing_latency(self):
        metrics = MetricsSummary(
            p95_ms=900, p99_ms=1500, error_rate=0.005,
            throughput_rps=140,
        )
        result = interpret(metrics, self._default_slo())
        assert result.status == "fail"
        failed = [c for c in result.checks if c["result"] == "fail"]
        assert len(failed) == 2  # p95 and p99 both fail

    def test_failing_error_rate(self):
        metrics = MetricsSummary(
            p95_ms=350, p99_ms=700, error_rate=0.05,
        )
        result = interpret(metrics, self._default_slo())
        assert result.status == "fail"
        error_check = [c for c in result.checks if c["metric"] == "error_rate"][0]
        assert error_check["result"] == "fail"

    def test_warning_on_high_cpu(self):
        metrics = MetricsSummary(
            p95_ms=350, p99_ms=700, error_rate=0.005,
            cpu_percent=92,
        )
        result = interpret(metrics, self._default_slo())
        assert result.status == "warning"
        assert any("CPU" in r for r in result.risks)

    def test_warning_on_high_memory(self):
        metrics = MetricsSummary(
            p95_ms=350, p99_ms=700, error_rate=0.005,
            memory_percent=88,
        )
        result = interpret(metrics, self._default_slo())
        assert result.status == "warning"
        assert any("memory" in r for r in result.risks)

    def test_missing_metrics_skipped(self):
        metrics = MetricsSummary()  # all None
        result = interpret(metrics, self._default_slo())
        skipped = [c for c in result.checks if c["result"] == "skip"]
        assert len(skipped) >= 2  # at least p95 and error_rate

    def test_narrative_contains_throughput(self):
        metrics = MetricsSummary(
            p95_ms=350, p99_ms=700, error_rate=0.005,
            throughput_rps=195,
        )
        result = interpret(metrics, self._default_slo())
        assert "195" in result.narrative
