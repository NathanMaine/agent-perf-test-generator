# Performance & Load Testing Assistant — SPEC (Prototype)

## Purpose and Scope
- Generate concise, tool-agnostic load test plans from a service profile and target SLOs.
- Optionally ingest simple result summaries to provide a lightweight interpretation.
- Record evidence that a plan/assessment was produced for a given service profile.
- Stay small, local-first, and easy to reason about; no test execution or dashboards.

## Personas
- **Individual engineer**: Wants a quick, structured load test plan and a sanity check on metrics.
- **Reviewer/teammate**: Wants to skim the plan and evidence log to understand what was tested.

## Key Concepts
- **Service profile**: Traffic expectations, key endpoints, SLOs, data risks, dependencies.
- **Load test plan**: Scenarios (steady, burst, soak), target rates/VUs/durations, checks, metrics to watch, expected pass/fail criteria.
- **Metrics summary (optional)**: Simple JSON/CSV with latency percentiles, error rates, throughput, resource utilization.
- **Evidence log**: Append-only record of plan/assessment events.

## Inputs
- Service profile file (YAML or JSON) with:
  - Service name/description
  - Critical endpoints or user journeys
  - Traffic shape (baseline rps, peaks, growth factors)
  - SLOs/SLIs (latency thresholds, error budgets)
  - Data constraints (PII, test data rules)
  - Dependencies (datastores, downstream services)
- Optional metrics summary (JSON/CSV) with at least: p50/p90/p95 latency, error rate, throughput; optional CPU/Mem/GC and saturation indicators.
- Optional existing evidence log for appending.

## Outputs
- Load test plan document containing:
  - Named scenarios: at minimum `steady`, `burst`, and `soak` (extendable with `stress` or `failover` when relevant)
  - Target load: rps or VU counts, stages (ramp-up/hold/ramp-down), durations
  - Checks: latency thresholds, error rate ceilings, success criteria per scenario
  - Metrics to watch: latency distribution, error classes, saturation (CPU/mem/IO), queue depth/backlog, GC pauses if applicable
  - Data/operational safety notes: test data handling, environment isolation, cleanup steps
- Optional interpretation summary when metrics are provided:
  - Pass/fail against declared SLOs and scenario-specific checks
  - Notable regressions vs. baseline (if baseline provided)
  - Obvious risks (e.g., high error rate during burst, saturation during soak)
- Evidence log entry:
  - Timestamp, service profile identifier, scenarios generated, whether interpretation ran, high-level outcome (`plan-generated`, `issues-detected`, `plan-and-interpretation-generated`).

## Functional Requirements
1. **Plan generation**
   - Validate the service profile shape and required fields.
   - Derive at least three scenarios (steady, burst, soak) with concrete targets and durations.
   - Emit scenario-specific checks aligned to SLOs/SLIs.
   - Emit guidance for data safety and environment isolation.
2. **Metrics interpretation (optional)**
   - Parse simple JSON/CSV summaries; tolerate missing fields with sensible warnings.
   - Evaluate metrics against SLO thresholds and scenario checks.
   - Produce a compact narrative: status, key numbers, and top risks.
3. **Evidence logging**
   - Append an entry per generation/interpretation run (JSON Lines recommended).
   - Avoid overwriting existing log entries.
4. **User interface**
   - Provide a CLI entry point to generate a plan from a service profile.
   - Provide a CLI option to ingest a metrics summary and emit an interpretation.
   - Provide a CLI option to append to the evidence log (path configurable).

## Non-Goals
- Executing load tests (delegate to k6, JMeter, Locust, etc.).
- Managing test data lifecycles or seeding environments.
- Advanced visualization or dashboards.
- Multi-tenant or distributed control-plane capabilities.

## Quality and Constraints
- Outputs should be deterministic given the same inputs (seed options acceptable).
- Keep dependencies light; prefer standard library where possible.
- All files should be plaintext/markdown/JSON; avoid proprietary formats.
- Clear error messages when inputs are invalid or incomplete.
- Respect data handling warnings; never assume production data is safe.

## Example Service Profile (YAML)
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

## Evidence Log Format (JSONL)
Each line represents an event:
```json
{"ts":"2024-01-02T15:04:05Z","service":"checkout-api","profile":"profiles/checkout.yaml","scenarios":["steady","burst","soak"],"interpretation":false,"outcome":"plan-generated"}
```

## First Increment (target)
- CLI that accepts a service profile and prints a load test plan (steady, burst, soak) to stdout and optionally writes to a file.
- Evidence log append with timestamp and scenario names.
- Skeleton parser for metrics summaries that validates fields and emits a short interpretation stub.

## Future Increments (optional)
- Diffing plans across profile revisions.
- Baseline comparison for metrics interpretation (regressions/highlights).
- Suggested k6/JMeter snippets for convenience (still tool-agnostic by default).
- Configuration for reusable thresholds and scenario templates.
