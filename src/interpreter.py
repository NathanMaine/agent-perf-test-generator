"""Parse metrics summaries and evaluate them against SLOs."""

import csv
import io
import json
import os
from typing import List, Optional, Tuple

from src.models import InterpretationResult, MetricsSummary, SLO


class MetricsParseError(Exception):
    """Raised when a metrics file cannot be parsed."""


def load_metrics(path: str) -> Tuple[MetricsSummary, List[str]]:
    """Load a metrics summary from JSON or CSV.

    Args:
        path: Path to the metrics file.

    Returns:
        A tuple of (MetricsSummary, warnings) where warnings list any
        missing or unparseable fields.

    Raises:
        MetricsParseError: If the file cannot be read or parsed.
    """
    if not os.path.isfile(path):
        raise MetricsParseError(f"metrics file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        return _load_json(path)
    elif ext == ".csv":
        return _load_csv(path)
    else:
        raise MetricsParseError(
            f"unsupported metrics format: {ext} (expected .json or .csv)"
        )


def interpret(metrics: MetricsSummary, slo: SLO) -> InterpretationResult:
    """Evaluate a MetricsSummary against an SLO and produce a narrative.

    Args:
        metrics: Parsed metrics summary.
        slo: SLO thresholds from the service profile.

    Returns:
        An InterpretationResult with status, narrative, check details, and risks.
    """
    checks = []
    risks = []
    any_fail = False

    # Latency checks
    latency_fields = {
        "p95": metrics.p95_ms,
        "p99": metrics.p99_ms,
    }
    for pct, value in latency_fields.items():
        threshold = slo.latency_ms.get(pct)
        if threshold is None:
            continue
        if value is None:
            checks.append({
                "metric": f"latency_{pct}",
                "result": "skip",
                "detail": f"{pct} latency not provided in metrics",
            })
            continue
        passed = value <= threshold
        checks.append({
            "metric": f"latency_{pct}",
            "result": "pass" if passed else "fail",
            "detail": f"{pct} latency: {value:.1f} ms (threshold: {threshold} ms)",
        })
        if not passed:
            any_fail = True

    # Error rate check
    if metrics.error_rate is not None:
        passed = metrics.error_rate <= slo.error_rate
        checks.append({
            "metric": "error_rate",
            "result": "pass" if passed else "fail",
            "detail": (
                f"error rate: {metrics.error_rate * 100:.2f}% "
                f"(threshold: {slo.error_rate * 100:.1f}%)"
            ),
        })
        if not passed:
            any_fail = True
    else:
        checks.append({
            "metric": "error_rate",
            "result": "skip",
            "detail": "error rate not provided in metrics",
        })

    # Resource saturation risks
    if metrics.cpu_percent is not None and metrics.cpu_percent > 80:
        risks.append(f"High CPU usage: {metrics.cpu_percent:.0f}%")
    if metrics.memory_percent is not None and metrics.memory_percent > 80:
        risks.append(f"High memory usage: {metrics.memory_percent:.0f}%")
    if metrics.gc_pause_ms is not None and metrics.gc_pause_ms > 100:
        risks.append(f"Elevated GC pause: {metrics.gc_pause_ms:.0f} ms")

    status = "fail" if any_fail else ("warning" if risks else "pass")
    narrative = _build_narrative(status, checks, risks, metrics)

    return InterpretationResult(
        status=status,
        narrative=narrative,
        checks=checks,
        risks=risks,
    )


# -- internal helpers ---------------------------------------------------------


_METRIC_FIELDS = [
    "p50_ms", "p90_ms", "p95_ms", "p99_ms",
    "error_rate", "throughput_rps",
    "cpu_percent", "memory_percent", "gc_pause_ms",
]


def _load_json(path: str) -> Tuple[MetricsSummary, List[str]]:
    try:
        with open(path, "r") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise MetricsParseError(f"failed to parse JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise MetricsParseError("metrics JSON must be an object at top level")

    return _dict_to_metrics(raw)


def _load_csv(path: str) -> Tuple[MetricsSummary, List[str]]:
    try:
        with open(path, "r") as f:
            content = f.read()
    except OSError as exc:
        raise MetricsParseError(f"failed to read CSV: {exc}") from exc

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise MetricsParseError("CSV file has no data rows")

    # Use the first row
    raw = {}
    for key, val in rows[0].items():
        key = key.strip()
        if key in _METRIC_FIELDS:
            try:
                raw[key] = float(val)
            except (ValueError, TypeError):
                pass  # will be caught as a warning
    return _dict_to_metrics(raw)


def _dict_to_metrics(raw: dict) -> Tuple[MetricsSummary, List[str]]:
    warnings = []
    kwargs = {}
    for field_name in _METRIC_FIELDS:
        val = raw.get(field_name)
        if val is None:
            warnings.append(f"missing field: {field_name}")
            kwargs[field_name] = None
        else:
            try:
                kwargs[field_name] = float(val)
            except (ValueError, TypeError):
                warnings.append(f"non-numeric value for {field_name}: {val!r}")
                kwargs[field_name] = None
    return MetricsSummary(**kwargs), warnings


def _build_narrative(
    status: str,
    checks: List[dict],
    risks: List[str],
    metrics: MetricsSummary,
) -> str:
    lines = []
    if status == "pass":
        lines.append("All SLO checks passed.")
    elif status == "fail":
        failed = [c for c in checks if c["result"] == "fail"]
        lines.append(f"SLO VIOLATION: {len(failed)} check(s) failed.")
        for c in failed:
            lines.append(f"  - {c['detail']}")
    else:
        lines.append("SLO checks passed, but risks were detected.")

    if metrics.throughput_rps is not None:
        lines.append(f"Throughput: {metrics.throughput_rps:.0f} rps")

    if risks:
        lines.append("Risks:")
        for r in risks:
            lines.append(f"  - {r}")

    return "\n".join(lines)
