"""Tests for service profile loading and validation."""

import json
import os
import tempfile

import pytest
import yaml

from src.loader import ProfileValidationError, load_profile


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestLoadProfileYAML:
    def test_load_valid_yaml(self):
        path = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        profile = load_profile(path)
        assert profile.service == "checkout-api"
        assert profile.traffic.baseline_rps == 50
        assert profile.traffic.peak_rps == 200
        assert profile.traffic.burst_factor == 3.0
        assert profile.slo.latency_ms["p95"] == 400
        assert profile.slo.latency_ms["p99"] == 800
        assert profile.slo.error_rate == 0.01
        assert len(profile.endpoints) == 2
        assert profile.endpoints[0].path == "/cart/submit"
        assert profile.endpoints[0].critical is True
        assert "payments-service" in profile.dependencies
        assert profile.data.uses_production_data is False

    def test_load_valid_json(self):
        path = os.path.join(FIXTURES_DIR, "checkout-profile.json")
        profile = load_profile(path)
        assert profile.service == "checkout-api"
        assert profile.traffic.baseline_rps == 50
        assert profile.slo.error_rate == 0.01


class TestProfileValidation:
    def test_missing_file(self):
        with pytest.raises(ProfileValidationError, match="not found"):
            load_profile("/nonexistent/path.yaml")

    def test_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"some text")
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="unsupported"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_missing_service_field(self):
        data = {
            "summary": "test",
            "traffic": {"baseline_rps": 10, "peak_rps": 50},
            "slo": {"latency_ms": {"p95": 200}, "error_rate": 0.01},
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="service"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_missing_traffic_field(self):
        data = {
            "service": "test-svc",
            "summary": "test",
            "slo": {"latency_ms": {"p95": 200}, "error_rate": 0.01},
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="traffic"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_missing_slo_field(self):
        data = {
            "service": "test-svc",
            "summary": "test",
            "traffic": {"baseline_rps": 10, "peak_rps": 50},
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="slo"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_invalid_json_content(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            f.write("{bad json")
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="parse"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_invalid_yaml_content(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False
        ) as f:
            f.write(":\n  :\n    - :\n  invalid: [")
            f.flush()
            try:
                with pytest.raises(ProfileValidationError):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_non_mapping_top_level(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump([1, 2, 3], f)
            f.flush()
            try:
                with pytest.raises(ProfileValidationError, match="mapping"):
                    load_profile(f.name)
            finally:
                os.unlink(f.name)

    def test_minimal_valid_profile(self):
        data = {
            "service": "minimal-svc",
            "summary": "",
            "traffic": {"baseline_rps": 10, "peak_rps": 100},
            "slo": {"latency_ms": {"p95": 500}, "error_rate": 0.02},
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            json.dump(data, f)
            f.flush()
            try:
                profile = load_profile(f.name)
                assert profile.service == "minimal-svc"
                assert profile.endpoints == []
                assert profile.dependencies == []
                assert profile.data.uses_production_data is False
            finally:
                os.unlink(f.name)
