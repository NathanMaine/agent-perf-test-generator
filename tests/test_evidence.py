"""Tests for evidence logging."""

import json
import os
import tempfile

from src.evidence import append_event, create_event, read_events


class TestCreateEvent:
    def test_basic_event(self):
        event = create_event(
            service="test-svc",
            profile_path="profiles/test.yaml",
            scenarios=["steady", "burst", "soak"],
        )
        assert event.service == "test-svc"
        assert event.profile == "profiles/test.yaml"
        assert event.scenarios == ["steady", "burst", "soak"]
        assert event.interpretation is False
        assert event.outcome == "plan-generated"
        assert "T" in event.ts  # ISO 8601

    def test_event_with_interpretation(self):
        event = create_event(
            service="test-svc",
            profile_path="profiles/test.yaml",
            scenarios=["steady"],
            interpretation=True,
            outcome="issues-detected",
        )
        assert event.interpretation is True
        assert event.outcome == "issues-detected"


class TestAppendAndRead:
    def test_append_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")
            assert not os.path.exists(log_path)

            event = create_event("svc", "p.yaml", ["steady"])
            append_event(event, log_path)

            assert os.path.isfile(log_path)
            with open(log_path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["service"] == "svc"

    def test_append_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")

            event1 = create_event("svc1", "p1.yaml", ["steady"])
            event2 = create_event("svc2", "p2.yaml", ["burst"])
            append_event(event1, log_path)
            append_event(event2, log_path)

            with open(log_path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["service"] == "svc1"
            assert json.loads(lines[1])["service"] == "svc2"

    def test_read_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")

            for i in range(3):
                event = create_event(f"svc-{i}", f"p{i}.yaml", ["steady"])
                append_event(event, log_path)

            events = read_events(log_path)
            assert len(events) == 3
            assert events[0].service == "svc-0"
            assert events[2].service == "svc-2"

    def test_read_nonexistent_returns_empty(self):
        events = read_events("/tmp/nonexistent_evidence.jsonl")
        assert events == []

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "nested", "dir", "evidence.jsonl")
            event = create_event("svc", "p.yaml", ["steady"])
            append_event(event, log_path)
            assert os.path.isfile(log_path)

    def test_malformed_lines_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")
            with open(log_path, "w") as f:
                f.write('{"service":"good","ts":"2024-01-01T00:00:00Z","profile":"p.yaml","scenarios":["steady"],"interpretation":false,"outcome":"plan-generated"}\n')
                f.write("this is not json\n")
                f.write('{"service":"also-good","ts":"2024-01-02T00:00:00Z","profile":"p2.yaml","scenarios":["burst"],"interpretation":false,"outcome":"plan-generated"}\n')

            events = read_events(log_path)
            assert len(events) == 2
            assert events[0].service == "good"
            assert events[1].service == "also-good"
