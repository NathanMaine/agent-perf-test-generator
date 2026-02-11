# Plan

- [x] Baseline documentation: README, DISCLAIMER, SPEC, constitution.
- [x] Define data shapes for service profiles, load plans, and evidence log entries.
- [x] Implement CLI to generate a load test plan from a service profile (steady, burst, soak scenarios).
- [x] Add evidence log append capability (JSONL) for each generation run.
- [x] Add metrics summary parser and interpretation stub aligned to SLOs.
- [x] Add tests for profile validation, plan generation, and evidence log append.
- [x] Provide usage examples in README once CLI exists.

## Near-Term Sequence

1. Define schema structs (service profile, scenario, plan, evidence event) and validation rules.
2. Implement plan generator producing steady/burst/soak scenarios with checks tied to SLOs.
3. Wire a CLI command: `plan --profile <path> [--out <path>] [--log <path>]`.
4. Implement evidence logging (append-only JSONL) when plan generation runs.
5. Implement metrics interpretation stub: parse JSON/CSV summary, evaluate against SLOs, emit narrative, optionally log outcome.
6. Add tests for validation and generator; include sample profiles and summaries under `fixtures/`.
7. Update README with CLI usage and examples.
