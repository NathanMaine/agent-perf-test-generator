# Performance & Load Testing Assistant (Prototype)

This repository contains a small, personal proof-of-concept for a **Performance & Load Testing Assistant**.

The goal is to experiment with a helper that can:

- Take a simple **service profile** and target SLOs
- Propose a **load test plan** (scenarios, rates, durations, and key checks)
- Optionally interpret **basic result metrics** and highlight obvious issues
- Capture a small **evidence record** that a testplan/assessment was produced

This is a personal R&D prototype, not a production performance testing platform.

## Goals

- Make it easier for an individual engineer to:
  - Describe a service, traffic shape, and SLOs
  - Get a **concrete load test plan** with stages and checks
  - Optionally get a quick **interpretation** of basic results
- Keep the implementation compact and understandable.

## Non-goals

- Full-blown performance testing framework
- Test execution engine (k6, JMeter, Locust, etc. remain separate tools)
- Complex visualization or dashboards

## Status

- [x] Initial specification (`SPEC.md`)
- [x] Minimal flow: service profile -> test plan suggestion
- [x] Optional basic result interpretation (e.g., from a JSON/CSV summary)
- [x] Simple evidence log (record that a plan/assessment was generated)
- [x] Run instructions in README

## How this repo is structured

- `SPEC.md` -- detailed specification for this prototype
- `DISCLAIMER.md` -- IP and usage disclaimer
- `memory/constitution.md` -- constraints/instructions for IDE agents
- `src/` -- Python implementation
  - `src/models.py` -- dataclasses for profiles, plans, scenarios, evidence events
  - `src/loader.py` -- service profile loader with validation
  - `src/generator.py` -- plan generator (steady, burst, soak scenarios)
  - `src/interpreter.py` -- metrics interpretation stub (JSON/CSV parsing, pass/fail)
  - `src/evidence.py` -- append-only JSONL evidence logging
  - `src/cli.py` -- Click CLI entry point
- `fixtures/` -- sample service profiles and metrics summaries
- `tests/` -- pytest test suite

---

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Generate a load test plan

```bash
python -m src.cli plan --profile fixtures/checkout-profile.yaml
```

This prints a JSON plan to stdout with three scenarios (steady, burst, soak), each including stages, checks aligned to SLOs, and metrics to watch.

### Write the plan to a file

```bash
python -m src.cli plan --profile fixtures/checkout-profile.yaml --out plan.json
```

### Generate a plan and log evidence

```bash
python -m src.cli plan --profile fixtures/checkout-profile.yaml --log evidence.jsonl
```

This appends a JSONL entry to `evidence.jsonl` recording the timestamp, service name, scenarios generated, and outcome.

### Generate a plan with metrics interpretation

```bash
python -m src.cli plan \
  --profile fixtures/checkout-profile.yaml \
  --metrics fixtures/metrics-passing.json \
  --log evidence.jsonl
```

When `--metrics` is provided, the tool also evaluates the metrics against the profile's SLOs and prints a pass/fail narrative.

### Interpret metrics standalone

```bash
python -m src.cli interpret-cmd \
  --profile fixtures/checkout-profile.yaml \
  --metrics fixtures/metrics-failing.json
```

### Run tests

```bash
python -m pytest tests/ -v
```

---

## Service Profile Format

Service profiles are YAML or JSON files describing the service under test. Example:

```yaml
service: checkout-api
summary: Handles checkout flows for web and mobile clients.
traffic:
  baseline_rps: 50
  peak_rps: 200
  burst_factor: 3
slo:
  latency_ms:
    p95: 400
    p99: 800
  error_rate: 0.01
endpoints:
  - path: /cart/submit
    method: POST
    critical: true
  - path: /cart/view
    method: GET
    critical: true
dependencies:
  - payments-service
  - inventory-service
data:
  uses_production_data: false
  notes: use synthetic carts and test payment tokens.
```

## Metrics Summary Format

Simple JSON or CSV files with latency percentiles, error rate, throughput, and optional resource utilization:

```json
{
  "p50_ms": 120,
  "p90_ms": 250,
  "p95_ms": 350,
  "p99_ms": 700,
  "error_rate": 0.005,
  "throughput_rps": 195,
  "cpu_percent": 55,
  "memory_percent": 62
}
```

## Evidence Log Format (JSONL)

Each line is a JSON object representing one event:

```json
{"ts":"2024-01-02T15:04:05Z","service":"checkout-api","profile":"fixtures/checkout-profile.yaml","scenarios":["steady","burst","soak"],"interpretation":false,"outcome":"plan-generated"}
```

Possible outcomes: `plan-generated`, `plan-and-interpretation-generated`, `issues-detected`.

---

See `SPEC.md` for detailed requirements.
