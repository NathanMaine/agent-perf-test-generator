"""Data models for service profiles, load test plans, and evidence events."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Endpoint:
    path: str
    method: str
    critical: bool = False


@dataclass
class TrafficShape:
    baseline_rps: int
    peak_rps: int
    burst_factor: float = 3.0


@dataclass
class SLO:
    latency_ms: dict = field(default_factory=dict)  # e.g. {"p95": 400, "p99": 800}
    error_rate: float = 0.01


@dataclass
class DataConstraints:
    uses_production_data: bool = False
    notes: str = ""


@dataclass
class ServiceProfile:
    service: str
    summary: str
    traffic: TrafficShape
    slo: SLO
    endpoints: List[Endpoint] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    data: Optional[DataConstraints] = None


@dataclass
class Check:
    metric: str
    operator: str  # "<=", "<", ">=", ">"
    threshold: float
    description: str = ""


@dataclass
class Stage:
    name: str  # "ramp-up", "hold", "ramp-down"
    duration_seconds: int
    target_rps: Optional[int] = None
    target_vus: Optional[int] = None


@dataclass
class Scenario:
    name: str  # "steady", "burst", "soak"
    description: str
    stages: List[Stage] = field(default_factory=list)
    checks: List[Check] = field(default_factory=list)
    metrics_to_watch: List[str] = field(default_factory=list)


@dataclass
class SafetyNotes:
    test_data_handling: str = ""
    environment_isolation: str = ""
    cleanup_steps: str = ""


@dataclass
class LoadTestPlan:
    service: str
    profile_path: str
    scenarios: List[Scenario] = field(default_factory=list)
    safety_notes: Optional[SafetyNotes] = None


@dataclass
class MetricsSummary:
    p50_ms: Optional[float] = None
    p90_ms: Optional[float] = None
    p95_ms: Optional[float] = None
    p99_ms: Optional[float] = None
    error_rate: Optional[float] = None
    throughput_rps: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    gc_pause_ms: Optional[float] = None


@dataclass
class InterpretationResult:
    status: str  # "pass", "fail", "warning"
    narrative: str
    checks: List[dict] = field(default_factory=list)  # each: {metric, result, detail}
    risks: List[str] = field(default_factory=list)


@dataclass
class EvidenceEvent:
    ts: str
    service: str
    profile: str
    scenarios: List[str] = field(default_factory=list)
    interpretation: bool = False
    outcome: str = "plan-generated"
