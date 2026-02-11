# Tasks

- [x] Define data models and validation rules for service profiles, scenarios, plans, and evidence events.
- [x] Create sample service profiles and metrics summaries under `fixtures/` for testing.
- [x] Implement plan generator that emits steady, burst, and soak scenarios with durations, target load, and checks tied to SLOs.
- [x] Implement CLI `plan --profile <path> [--out <path>] [--log <path>]` to generate plans and optionally append evidence.
- [x] Implement metrics interpretation stub to parse JSON/CSV summaries and emit a short narrative plus pass/fail status.
- [x] Add append-only evidence logging (JSONL) with timestamp, profile path, scenarios generated, and outcome.
- [x] Add tests covering profile validation, plan generation, and evidence logging; document fixtures and expected outputs.
- [x] Update README with usage examples and describe evidence log format once CLI exists.
