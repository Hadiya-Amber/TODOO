Client-side latency harness (placeholder)
========================================

This directory will contain the client-side harness used to exercise the
application endpoints and measure latency from the client's perspective.

Intended contents:
- run_latency_test.py - a small script that performs HTTP requests against
  the running application and reports latency statistics (p50, p95, p99).
- data/ - optional directory to store generated reports and samples.

Invocation (future):

```bash
python client_harness/run_latency_test.py --target http://localhost:8000
```

Server runtime
--------------

When running the client harness locally you will need a running server.
Follow the "Local development" section in the repository README to start the
server. As a convenience, the canonical development run command is:

```bash
uvicorn app.main:app --reload --port 8000
```

CI usage:

- CI can invoke the harness as part of a job that measures latency and
  gates commits by failing when latency budgets are exceeded. The CI workflow
  contains a placeholder job slot for latency gating.

This README is a placeholder and should be expanded when the harness is
implemented.
