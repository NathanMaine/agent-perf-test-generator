# Agent-Driven Performance Test Generator

Before a big sale (like Black Friday), this AI writes a script to simulate thousands of fake users visiting a website all at once.
It checks if the site will crash, without a human needing to write the complex test code.

## What This Is

A CLI that:

- Accepts a natural language spec of load testing needs.
- Produces a simple Taurus-style YAML file.
- Targets a toy/mock HTTP service.

## IP-Safety Boundaries

- Only generates basic YAML; no advanced parameter correlation.
- No proprietary benchmarking formulas.
- Safe as a generic example.

## Files

- `src/main.py` -- CLI.
- `src/generator.py` -- YAML generator.
- `mock_service/app.py` -- toy HTTP endpoint for testing.

## Example

```bash
python src/main.py \
  --spec "100 users over 2 minutes hitting GET /api/demo" \
  --output out/test.yaml
```
