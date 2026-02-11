"""Generate load test plans from a validated service profile."""

import json
from dataclasses import asdict
from typing import List

from src.models import (
    Check,
    LoadTestPlan,
    SafetyNotes,
    Scenario,
    ServiceProfile,
    Stage,
)


def generate_plan(profile: ServiceProfile, profile_path: str) -> LoadTestPlan:
    """Produce a LoadTestPlan with steady, burst, and soak scenarios.

    Args:
        profile: A validated ServiceProfile.
        profile_path: Filesystem path to the source profile (for logging).

    Returns:
        A LoadTestPlan with concrete scenarios, checks, and safety notes.
    """
    scenarios = [
        _steady_scenario(profile),
        _burst_scenario(profile),
        _soak_scenario(profile),
    ]
    safety = _safety_notes(profile)
    return LoadTestPlan(
        service=profile.service,
        profile_path=profile_path,
        scenarios=scenarios,
        safety_notes=safety,
    )


def plan_to_dict(plan: LoadTestPlan) -> dict:
    """Convert a LoadTestPlan to a plain dict suitable for JSON serialization."""
    return asdict(plan)


def plan_to_json(plan: LoadTestPlan, indent: int = 2) -> str:
    """Serialize a LoadTestPlan to a JSON string."""
    return json.dumps(plan_to_dict(plan), indent=indent)


# -- scenario builders --------------------------------------------------------


def _common_checks(profile: ServiceProfile) -> List[Check]:
    """Build checks derived from the profile SLOs."""
    checks = []
    for pct, threshold in profile.slo.latency_ms.items():
        checks.append(
            Check(
                metric=f"latency_{pct}",
                operator="<=",
                threshold=float(threshold),
                description=f"{pct} latency must be <= {threshold} ms",
            )
        )
    checks.append(
        Check(
            metric="error_rate",
            operator="<=",
            threshold=profile.slo.error_rate,
            description=f"error rate must be <= {profile.slo.error_rate * 100:.1f}%",
        )
    )
    return checks


_COMMON_METRICS = [
    "latency_p50",
    "latency_p90",
    "latency_p95",
    "latency_p99",
    "error_rate",
    "throughput_rps",
    "cpu_percent",
    "memory_percent",
]


def _steady_scenario(profile: ServiceProfile) -> Scenario:
    baseline = profile.traffic.baseline_rps
    return Scenario(
        name="steady",
        description=(
            f"Sustain baseline traffic at {baseline} rps for 10 minutes "
            "to validate normal-operation SLOs."
        ),
        stages=[
            Stage(name="ramp-up", duration_seconds=60, target_rps=baseline),
            Stage(name="hold", duration_seconds=600, target_rps=baseline),
            Stage(name="ramp-down", duration_seconds=30, target_rps=0),
        ],
        checks=_common_checks(profile),
        metrics_to_watch=list(_COMMON_METRICS),
    )


def _burst_scenario(profile: ServiceProfile) -> Scenario:
    peak = profile.traffic.peak_rps
    burst_rps = int(peak * profile.traffic.burst_factor)
    baseline = profile.traffic.baseline_rps
    checks = _common_checks(profile)
    # Relax latency thresholds during burst by 50%
    burst_checks = []
    for c in checks:
        if c.metric.startswith("latency_"):
            burst_checks.append(
                Check(
                    metric=c.metric,
                    operator=c.operator,
                    threshold=c.threshold * 1.5,
                    description=f"(burst-relaxed) {c.metric} <= {c.threshold * 1.5:.0f} ms",
                )
            )
        else:
            burst_checks.append(c)
    return Scenario(
        name="burst",
        description=(
            f"Spike from {baseline} rps to {burst_rps} rps over 30 seconds, "
            "hold for 2 minutes, then return to baseline. "
            "Validates behaviour under sudden traffic surges."
        ),
        stages=[
            Stage(name="ramp-up", duration_seconds=60, target_rps=baseline),
            Stage(name="hold-baseline", duration_seconds=120, target_rps=baseline),
            Stage(name="spike", duration_seconds=30, target_rps=burst_rps),
            Stage(name="hold-burst", duration_seconds=120, target_rps=burst_rps),
            Stage(name="recover", duration_seconds=60, target_rps=baseline),
            Stage(name="ramp-down", duration_seconds=30, target_rps=0),
        ],
        checks=burst_checks,
        metrics_to_watch=list(_COMMON_METRICS),
    )


def _soak_scenario(profile: ServiceProfile) -> Scenario:
    baseline = profile.traffic.baseline_rps
    return Scenario(
        name="soak",
        description=(
            f"Run at baseline ({baseline} rps) for 60 minutes "
            "to detect slow leaks, connection exhaustion, or GC pressure."
        ),
        stages=[
            Stage(name="ramp-up", duration_seconds=120, target_rps=baseline),
            Stage(name="hold", duration_seconds=3600, target_rps=baseline),
            Stage(name="ramp-down", duration_seconds=60, target_rps=0),
        ],
        checks=_common_checks(profile) + [
            Check(
                metric="memory_percent",
                operator="<=",
                threshold=85.0,
                description="memory usage must stay below 85% during soak",
            ),
            Check(
                metric="cpu_percent",
                operator="<=",
                threshold=80.0,
                description="CPU usage must stay below 80% during soak",
            ),
        ],
        metrics_to_watch=list(_COMMON_METRICS) + ["gc_pause_ms"],
    )


def _safety_notes(profile: ServiceProfile) -> SafetyNotes:
    data = profile.data
    if data and data.uses_production_data:
        test_data = (
            "WARNING: profile indicates production data may be in use. "
            "Ensure PII masking and data-handling policies are followed."
        )
    elif data and data.notes:
        test_data = data.notes
    else:
        test_data = "Use synthetic/test data only."

    deps = ", ".join(profile.dependencies) if profile.dependencies else "none listed"
    env_isolation = (
        f"Ensure load tests run against an isolated environment. "
        f"Dependencies ({deps}) should be stubbed or provisioned in test mode."
    )

    cleanup = (
        "After test completion, tear down any provisioned test data "
        "and verify no side-effects leaked to shared environments."
    )

    return SafetyNotes(
        test_data_handling=test_data,
        environment_isolation=env_isolation,
        cleanup_steps=cleanup,
    )
