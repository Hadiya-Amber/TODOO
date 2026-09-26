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
uvicorn app.main:app --reload --port 8000
# or (alternative) python -m uvicorn app.main:app --reload --port 8000
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

Common local-run failures and how to diagnose them
-------------------------------------------------

- Port already in use

  If uvicorn fails to bind the requested port (default 8000) you will see
  an error message such as "Address already in use". Either stop the process
  using the port or start the server on a different port via the `--port`
  flag:

  ```bash
  uvicorn app.main:app --reload --port 8001
  ```

- Missing dependencies / import errors

  Ensure your virtual environment is activated and dependencies are
  installed (`pip install -r requirements.in`). If a third-party import
  fails when running the app or tests, install the missing package into
  your virtualenv.

- Permission denied when accessing the JSON persistence store

  If the server logs contain a permission denied error when reading or
  writing the JSON store, verify the path and permissions as described in
  persistence/README.md. A quick way to print the path the app will use is:

  ```bash
  python -c "from app.persistence import get_data_file_path; print(get_data_file_path())"
  ```

  Then inspect permissions:

  ```bash
  ls -l <path>
  stat <path>
  ```

  If the parent directory does not exist, create it and set ownership to
  your development user and mode 0755 (directories) / 0640 or 0644 (files):

  ```bash
  mkdir -p "$(dirname <path>)"
  chown $(id -u):$(id -g) "$(dirname <path>)"
  chmod 0755 "$(dirname <path>)"
  ```

  You can also create an initial empty store from the Python REPL or a one-liner:

  ```bash
  python -c "from app.persistence import save_store; save_store([])"
  ```

  See persistence/README.md for more details and recommendations about
  permissions, ownership and durability.

## Developer checklist

- [ ] Clone the repo
- [ ] Create and activate a virtualenv
- [ ] pip install -r requirements.in
- [ ] Export required environment variables
- [ ] Run `python -m pytest -q` to verify tests

For more details see the contributing guidelines or open an issue if something is unclear.
