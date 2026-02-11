"""Tests for plan generation."""

import json
import os

from src.generator import generate_plan, plan_to_dict, plan_to_json
from src.loader import load_profile


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _load_checkout_profile():
    path = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
    return load_profile(path), path


class TestGeneratePlan:
    def test_produces_three_scenarios(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        assert len(plan.scenarios) == 3
        names = [s.name for s in plan.scenarios]
        assert "steady" in names
        assert "burst" in names
        assert "soak" in names

    def test_service_name_propagated(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        assert plan.service == "checkout-api"
        assert plan.profile_path == path

    def test_steady_scenario_uses_baseline_rps(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        steady = [s for s in plan.scenarios if s.name == "steady"][0]
        hold_stages = [st for st in steady.stages if st.name == "hold"]
        assert len(hold_stages) == 1
        assert hold_stages[0].target_rps == 50  # baseline_rps

    def test_burst_scenario_uses_burst_factor(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        burst = [s for s in plan.scenarios if s.name == "burst"][0]
        spike_stages = [st for st in burst.stages if st.name == "spike"]
        assert len(spike_stages) == 1
        # peak_rps (200) * burst_factor (3) = 600
        assert spike_stages[0].target_rps == 600

    def test_soak_scenario_has_long_duration(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        soak = [s for s in plan.scenarios if s.name == "soak"][0]
        hold_stages = [st for st in soak.stages if st.name == "hold"]
        assert len(hold_stages) == 1
        assert hold_stages[0].duration_seconds >= 3600  # at least 60 min

    def test_checks_aligned_to_slos(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        steady = [s for s in plan.scenarios if s.name == "steady"][0]
        check_metrics = [c.metric for c in steady.checks]
        assert "latency_p95" in check_metrics
        assert "latency_p99" in check_metrics
        assert "error_rate" in check_metrics

    def test_slo_thresholds_in_steady_checks(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        steady = [s for s in plan.scenarios if s.name == "steady"][0]
        p95_check = [c for c in steady.checks if c.metric == "latency_p95"][0]
        assert p95_check.threshold == 400.0
        assert p95_check.operator == "<="

    def test_burst_has_relaxed_latency_thresholds(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        burst = [s for s in plan.scenarios if s.name == "burst"][0]
        p95_check = [c for c in burst.checks if c.metric == "latency_p95"][0]
        # 400 * 1.5 = 600
        assert p95_check.threshold == 600.0

    def test_soak_has_resource_checks(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        soak = [s for s in plan.scenarios if s.name == "soak"][0]
        check_metrics = [c.metric for c in soak.checks]
        assert "memory_percent" in check_metrics
        assert "cpu_percent" in check_metrics

    def test_safety_notes_present(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        assert plan.safety_notes is not None
        assert "synthetic" in plan.safety_notes.test_data_handling.lower() or \
               "test" in plan.safety_notes.test_data_handling.lower()
        assert "payments-service" in plan.safety_notes.environment_isolation

    def test_metrics_to_watch_populated(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        for scenario in plan.scenarios:
            assert len(scenario.metrics_to_watch) > 0


class TestPlanSerialization:
    def test_plan_to_json_valid(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        json_str = plan_to_json(plan)
        parsed = json.loads(json_str)
        assert parsed["service"] == "checkout-api"
        assert len(parsed["scenarios"]) == 3

    def test_plan_to_dict_round_trip(self):
        profile, path = _load_checkout_profile()
        plan = generate_plan(profile, path)
        d = plan_to_dict(plan)
        assert isinstance(d, dict)
        assert d["service"] == plan.service
        assert len(d["scenarios"]) == len(plan.scenarios)

    def test_json_output_deterministic(self):
        profile, path = _load_checkout_profile()
        plan1 = generate_plan(profile, path)
        plan2 = generate_plan(profile, path)
        assert plan_to_json(plan1) == plan_to_json(plan2)
