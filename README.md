# TODOO - Developer Guide

This developer README helps contributors bootstrap the repository locally, run the test suite, and understand the source layout.

## Checkout

Clone the repository:

```bash
git clone https://github.com/Hadiya-Amber/TODOO.git
cd TODOO
```

## Install

Create and activate a virtual environment, then install runtime and test dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.in
```

If a requirements.in file is not present, at minimum install pytest for running tests:

```bash
pip install pytest
```

## Required environment variables

The application expects a few environment variables to be set in your shell or via a .env file. Example placeholders:

- TODOO_DATA_FILE: Path to the JSON persistence file (e.g. ./data/todoo.json)
- SECRET_KEY: an application secret used for signing or sessions

You can export them manually:

```bash
export TODOO_DATA_FILE=./data/todoo.json
export SECRET_KEY=mydevsecret
```

## One-line run command

To start the application locally (development):

```bash
uvicorn todoo.main:app --reload
# or (alternative) python -m uvicorn todoo.main:app --reload
```

If the run artifact referenced by other tasks exists, follow that project's run command instead.

## Repository layout (developer view)

The layout below identifies where to add features without reorganising the repo:

- todoo/ or app/ - FastAPI application code (HTTP handlers, models, dependencies)
- tests/ - Unit and integration tests (pytest)
- instrumentation/ or metrics/ - Telemetry, tracing, and metrics-related code
- client/ or web/ - Client-side harness, server-rendered templates or JS

This README expects the project to use FastAPI for the backend and uvicorn as the ASGI server.

## Linting and tests (local)

Run lint checks (recommended):

```bash
pip install ruff
ruff check .
```

Run the test suite:

```bash
python -m pytest -q
```

## Troubleshooting

- If tests fail with import errors, ensure your virtualenv is activated and dependencies are installed.
- If environment variables are missing, double-check they are exported or present in your .env before running the app or tests.
- If the CI pipeline shows missing configuration or secrets, the workflow is designed to fail visibly — do not add secrets into the repository.

## Developer checklist

- [ ] Clone the repo
- [ ] Create and activate a virtualenv
- [ ] pip install -r requirements.in
- [ ] Export required environment variables
- [ ] Run `python -m pytest -q` to verify tests

For more details see the contributing guidelines or open an issue if something is unclear.
