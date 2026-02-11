"""Tests for the CLI entry point."""

import json
import os
import tempfile

from click.testing import CliRunner

from src.cli import main


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class TestPlanCommand:
    def test_plan_to_stdout(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "--profile", profile])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["service"] == "checkout-api"
        assert len(parsed["scenarios"]) == 3

    def test_plan_to_file(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "plan.json")
            runner = CliRunner()
            result = runner.invoke(
                main, ["plan", "--profile", profile, "--out", out_path]
            )
            assert result.exit_code == 0
            assert os.path.isfile(out_path)
            with open(out_path, "r") as f:
                parsed = json.loads(f.read())
            assert parsed["service"] == "checkout-api"

    def test_plan_with_evidence_log(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")
            runner = CliRunner()
            result = runner.invoke(
                main, ["plan", "--profile", profile, "--log", log_path]
            )
            assert result.exit_code == 0
            assert os.path.isfile(log_path)
            with open(log_path, "r") as f:
                lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["service"] == "checkout-api"
            assert "steady" in entry["scenarios"]

    def test_plan_with_passing_metrics(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        metrics = os.path.join(FIXTURES_DIR, "metrics-passing.json")
        runner = CliRunner()
        result = runner.invoke(
            main, ["plan", "--profile", profile, "--metrics", metrics]
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_plan_with_failing_metrics(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        metrics = os.path.join(FIXTURES_DIR, "metrics-failing.json")
        runner = CliRunner()
        result = runner.invoke(
            main, ["plan", "--profile", profile, "--metrics", metrics]
        )
        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_plan_with_metrics_and_log(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        metrics = os.path.join(FIXTURES_DIR, "metrics-failing.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "evidence.jsonl")
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "plan",
                    "--profile", profile,
                    "--metrics", metrics,
                    "--log", log_path,
                ],
            )
            assert result.exit_code == 0
            with open(log_path, "r") as f:
                entry = json.loads(f.readline())
            assert entry["interpretation"] is True
            assert entry["outcome"] == "issues-detected"

    def test_invalid_profile_exits_with_error(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"not": "a profile"}, f)
            f.flush()
            try:
                runner = CliRunner()
                result = runner.invoke(main, ["plan", "--profile", f.name])
                assert result.exit_code != 0
            finally:
                os.unlink(f.name)


class TestInterpretCommand:
    def test_interpret_passing(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        metrics = os.path.join(FIXTURES_DIR, "metrics-passing.json")
        runner = CliRunner()
        result = runner.invoke(
            main, ["interpret-cmd", "--profile", profile, "--metrics", metrics]
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_interpret_failing(self):
        profile = os.path.join(FIXTURES_DIR, "checkout-profile.yaml")
        metrics = os.path.join(FIXTURES_DIR, "metrics-failing.json")
        runner = CliRunner()
        result = runner.invoke(
            main, ["interpret-cmd", "--profile", profile, "--metrics", metrics]
        )
        assert result.exit_code == 0
        assert "FAIL" in result.output
