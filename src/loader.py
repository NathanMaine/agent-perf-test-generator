"""Load and validate service profile files (YAML or JSON)."""

import json
import os
from typing import List

import yaml

from src.models import (
    DataConstraints,
    Endpoint,
    SLO,
    ServiceProfile,
    TrafficShape,
)


class ProfileValidationError(Exception):
    """Raised when a service profile fails validation."""


def load_profile(path: str) -> ServiceProfile:
    """Load a service profile from a YAML or JSON file.

    Args:
        path: Path to the profile file.

    Returns:
        A validated ServiceProfile instance.

    Raises:
        ProfileValidationError: If the file is missing, unreadable, or invalid.
    """
    if not os.path.isfile(path):
        raise ProfileValidationError(f"profile file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "r") as f:
            if ext in (".yaml", ".yml"):
                raw = yaml.safe_load(f)
            elif ext == ".json":
                raw = json.load(f)
            else:
                raise ProfileValidationError(
                    f"unsupported file extension: {ext} (expected .yaml, .yml, or .json)"
                )
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ProfileValidationError(f"failed to parse {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProfileValidationError("profile must be a mapping/object at the top level")

    return _build_profile(raw)


def _build_profile(raw: dict) -> ServiceProfile:
    """Construct and validate a ServiceProfile from a raw dict."""
    errors: List[str] = []

    service = raw.get("service")
    if not service or not isinstance(service, str):
        errors.append("'service' is required and must be a non-empty string")

    summary = raw.get("summary", "")

    traffic_raw = raw.get("traffic")
    if not isinstance(traffic_raw, dict):
        errors.append("'traffic' is required and must be a mapping")
        traffic = None
    else:
        traffic = _parse_traffic(traffic_raw, errors)

    slo_raw = raw.get("slo")
    if not isinstance(slo_raw, dict):
        errors.append("'slo' is required and must be a mapping")
        slo = None
    else:
        slo = _parse_slo(slo_raw, errors)

    endpoints = _parse_endpoints(raw.get("endpoints", []), errors)
    dependencies = raw.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("'dependencies' must be a list")
        dependencies = []

    data = _parse_data(raw.get("data"))

    if errors:
        raise ProfileValidationError(
            "profile validation failed:\n  - " + "\n  - ".join(errors)
        )

    return ServiceProfile(
        service=service,
        summary=summary,
        traffic=traffic,
        slo=slo,
        endpoints=endpoints,
        dependencies=dependencies,
        data=data,
    )


def _parse_traffic(raw: dict, errors: List[str]) -> TrafficShape:
    baseline = raw.get("baseline_rps")
    peak = raw.get("peak_rps")
    burst = raw.get("burst_factor", 3.0)

    if baseline is None or not isinstance(baseline, (int, float)):
        errors.append("'traffic.baseline_rps' is required and must be a number")
        baseline = 0
    if peak is None or not isinstance(peak, (int, float)):
        errors.append("'traffic.peak_rps' is required and must be a number")
        peak = 0

    return TrafficShape(
        baseline_rps=int(baseline),
        peak_rps=int(peak),
        burst_factor=float(burst),
    )


def _parse_slo(raw: dict, errors: List[str]) -> SLO:
    latency_ms = raw.get("latency_ms", {})
    if not isinstance(latency_ms, dict):
        errors.append("'slo.latency_ms' must be a mapping")
        latency_ms = {}
    error_rate = raw.get("error_rate", 0.01)
    if not isinstance(error_rate, (int, float)):
        errors.append("'slo.error_rate' must be a number")
        error_rate = 0.01
    return SLO(latency_ms=latency_ms, error_rate=float(error_rate))


def _parse_endpoints(raw: list, errors: List[str]) -> List[Endpoint]:
    if not isinstance(raw, list):
        errors.append("'endpoints' must be a list")
        return []
    endpoints = []
    for i, ep in enumerate(raw):
        if not isinstance(ep, dict):
            errors.append(f"endpoints[{i}] must be a mapping")
            continue
        path = ep.get("path", "")
        method = ep.get("method", "GET")
        critical = ep.get("critical", False)
        if not path:
            errors.append(f"endpoints[{i}].path is required")
        endpoints.append(Endpoint(path=path, method=method, critical=critical))
    return endpoints


def _parse_data(raw) -> DataConstraints:
    if raw is None or not isinstance(raw, dict):
        return DataConstraints()
    return DataConstraints(
        uses_production_data=bool(raw.get("uses_production_data", False)),
        notes=str(raw.get("notes", "")),
    )
