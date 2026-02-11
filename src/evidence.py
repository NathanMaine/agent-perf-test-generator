"""Append-only evidence logging in JSONL format."""

import json
import os
from datetime import datetime, timezone
from typing import List

from src.models import EvidenceEvent


def create_event(
    service: str,
    profile_path: str,
    scenarios: List[str],
    interpretation: bool = False,
    outcome: str = "plan-generated",
) -> EvidenceEvent:
    """Build an EvidenceEvent with the current UTC timestamp.

    Args:
        service: Name of the service.
        profile_path: Path to the source profile file.
        scenarios: List of scenario names that were generated.
        interpretation: Whether metrics interpretation was also run.
        outcome: High-level outcome label.

    Returns:
        A populated EvidenceEvent.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return EvidenceEvent(
        ts=ts,
        service=service,
        profile=profile_path,
        scenarios=scenarios,
        interpretation=interpretation,
        outcome=outcome,
    )


def append_event(event: EvidenceEvent, log_path: str) -> None:
    """Append a single evidence event as a JSONL line.

    Creates the file (and parent directories) if it does not exist.
    Never overwrites existing entries.

    Args:
        event: The event to log.
        log_path: Filesystem path to the JSONL evidence log.
    """
    parent = os.path.dirname(log_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    line = json.dumps({
        "ts": event.ts,
        "service": event.service,
        "profile": event.profile,
        "scenarios": event.scenarios,
        "interpretation": event.interpretation,
        "outcome": event.outcome,
    })

    with open(log_path, "a") as f:
        f.write(line + "\n")


def read_events(log_path: str) -> List[EvidenceEvent]:
    """Read all events from a JSONL evidence log.

    Args:
        log_path: Path to the evidence log.

    Returns:
        List of EvidenceEvent instances. Malformed lines are skipped.
    """
    if not os.path.isfile(log_path):
        return []

    events = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                events.append(EvidenceEvent(
                    ts=raw.get("ts", ""),
                    service=raw.get("service", ""),
                    profile=raw.get("profile", ""),
                    scenarios=raw.get("scenarios", []),
                    interpretation=raw.get("interpretation", False),
                    outcome=raw.get("outcome", ""),
                ))
            except json.JSONDecodeError:
                continue
    return events
