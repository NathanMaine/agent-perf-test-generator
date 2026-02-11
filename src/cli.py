"""CLI entry point for the performance load testing assistant."""

import json
import sys

import click

from src.evidence import append_event, create_event
from src.generator import generate_plan, plan_to_json
from src.interpreter import interpret, load_metrics
from src.loader import ProfileValidationError, load_profile


@click.group()
def main():
    """Performance & Load Testing Assistant -- generate load test plans from service profiles."""


@main.command()
@click.option(
    "--profile",
    required=True,
    type=click.Path(exists=True),
    help="Path to a service profile file (YAML or JSON).",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(),
    help="Optional output path for the generated plan (JSON). Prints to stdout if omitted.",
)
@click.option(
    "--log",
    "log_path",
    default=None,
    type=click.Path(),
    help="Optional path to the evidence log (JSONL). Appends an entry when provided.",
)
@click.option(
    "--metrics",
    default=None,
    type=click.Path(exists=True),
    help="Optional path to a metrics summary (JSON or CSV) for interpretation.",
)
def plan(profile, out, log_path, metrics):
    """Generate a load test plan from a service profile."""
    try:
        svc_profile = load_profile(profile)
    except ProfileValidationError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    test_plan = generate_plan(svc_profile, profile)
    plan_json = plan_to_json(test_plan)

    if out:
        with open(out, "w") as f:
            f.write(plan_json + "\n")
        click.echo(f"Plan written to {out}")
    else:
        click.echo(plan_json)

    # Determine outcome and handle optional interpretation
    interpretation_ran = False
    outcome = "plan-generated"

    if metrics:
        try:
            metrics_data, warnings = load_metrics(metrics)
            for w in warnings:
                click.echo(f"Warning: {w}", err=True)
            result = interpret(metrics_data, svc_profile.slo)
            interpretation_ran = True
            click.echo("\n--- Metrics Interpretation ---")
            click.echo(f"Status: {result.status.upper()}")
            click.echo(result.narrative)
            if result.status == "fail":
                outcome = "issues-detected"
            else:
                outcome = "plan-and-interpretation-generated"
        except Exception as exc:
            click.echo(f"Warning: could not interpret metrics: {exc}", err=True)

    if log_path:
        scenario_names = [s.name for s in test_plan.scenarios]
        event = create_event(
            service=svc_profile.service,
            profile_path=profile,
            scenarios=scenario_names,
            interpretation=interpretation_ran,
            outcome=outcome,
        )
        append_event(event, log_path)
        click.echo(f"Evidence logged to {log_path}")


@main.command()
@click.option(
    "--metrics",
    required=True,
    type=click.Path(exists=True),
    help="Path to a metrics summary file (JSON or CSV).",
)
@click.option(
    "--profile",
    required=True,
    type=click.Path(exists=True),
    help="Path to the service profile to evaluate against.",
)
def interpret_cmd(metrics, profile):
    """Interpret a metrics summary against a service profile's SLOs."""
    try:
        svc_profile = load_profile(profile)
    except ProfileValidationError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        metrics_data, warnings = load_metrics(metrics)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    for w in warnings:
        click.echo(f"Warning: {w}", err=True)

    result = interpret(metrics_data, svc_profile.slo)
    click.echo(f"Status: {result.status.upper()}")
    click.echo(result.narrative)

    output = {
        "status": result.status,
        "checks": result.checks,
        "risks": result.risks,
    }
    click.echo("\n" + json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
