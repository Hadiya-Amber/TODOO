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

The application expects a few environment variables to be set in your shell or via a .env file. Example placeholders (the code resolves the JSON store from TODOS_JSON_PATH - see app/persistence.py::get_data_file_path):

- TODOS_JSON_PATH: Path to the JSON persistence file (e.g. ./data/todoo.json or /var/lib/todoo/todos.json)
- SECRET_KEY: an application secret used for signing or sessions

You can export them manually:

```bash
export TODOS_JSON_PATH=./data/todoo.json
export SECRET_KEY=mydevsecret
```

## Local runtime / VM startup

This section shows one-line uvicorn commands, environment variables, and example HTTP requests you can run on a single VM to start the FastAPI ASGI server and exercise the /api/todos endpoints. Replace placeholders in angle brackets (e.g. <HOST>, <PORT>, <PATH>) with real values.

One-line uvicorn examples (placeholders):

```bash
# Start on localhost with an explicit JSON store path
export TODOS_JSON_PATH=<PATH_TO_JSON_STORE>  # e.g. /var/lib/todoo/todos.json or ./data/todoo.json
uvicorn app.main:app --host <HOST> --port <PORT>

# Example using loopback defaults:
export TODOS_JSON_PATH=./data/todoo.json
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Bind to all interfaces (VM-facing):
export TODOS_JSON_PATH=/var/lib/todoo/todos.json
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Notes:
- The application resolves the JSON persistence file from TODOS_JSON_PATH. See persistence/README.md for verification and recommended permissions.
- If your environment uses a different variable name, the authoritative resolver in the code is get_data_file_path in app/persistence.py (run: python -c "from app.persistence import get_data_file_path; print(get_data_file_path())").

Quick exercise: example HTTP requests for /api/todos

Below are curl examples that exercise the create, edit, toggle (partial-update), delete and list (GET) flows. They assume the server is reachable at http://<HOST>:<PORT> and the API root is /api/todos.

1) Create a todo (POST)

```bash
curl -sS -X POST "http://<HOST>:<PORT>/api/todos" \
  -H "Content-Type: application/json" \
  -d '{"label":"Buy milk"}'
# Expected: 201 Created with JSON body for the created todo containing an "id", "label", and "done" fields
```

2) List todos (GET)

```bash
curl -sS "http://<HOST>:<PORT>/api/todos"
# Expected: 200 OK with JSON array containing created items
```

3) Edit a todo (PUT)

```bash
curl -sS -X PUT "http://<HOST>:<PORT>/api/todos/<ID>" \
  -H "Content-Type: application/json" \
  -d '{"label":"Buy almond milk"}'
# Expected: 200 OK with updated todo in response
```

4) Toggle a todo's done state (PATCH)

```bash
curl -sS -X PATCH "http://<HOST>:<PORT>/api/todos/<ID>/toggle"
# Expected: 200 OK with todo showing toggled "done" boolean
```

5) Delete a todo (DELETE)

```bash
curl -sS -X DELETE "http://<HOST>:<PORT>/api/todos/<ID>"
# Expected: 204 No Content (or 200 OK) and subsequent GET should not include the item
```

Verify persistence across restart

1. Start the server with a persistent path: export TODOS_JSON_PATH=./data/todoo.json; uvicorn app.main:app --host 127.0.0.1 --port 8000
2. Create a todo using the POST example above
3. Stop the server (Ctrl-C) and restart it with the same TODOS_JSON_PATH
4. Run GET /api/todos — the previously created todo should still be present in the list

Troubleshooting and remediation

Missing or unwritable JSON file

- Symptom: Server fails on startup with an exception mentioning the data file path or a traceback including PermissionError or RuntimeError from app.persistence.validate_data_file.
- Exact messages observed from the code on startup when the file or its directory is missing or not writable (examples you may see):
  - "FileNotFoundError: [Errno 2] No such file or directory: '<path>'"
  - "PermissionError: [Errno 13] Permission denied: '<path>'"
  - RuntimeError from the persistence resolver with one of these exact messages:

    - "persistence: parent directory for JSON store does not exist: <path>\nRemediation: create the parent directory or change TODOS_JSON_PATH to a writable location."

    - "persistence: configured JSON store is not writable: <path>\nRemediation: adjust file permissions or ownership so the process can write to the file."

    - "persistence: unable to create initial JSON store at <path>: <os error>\nRemediation: ensure the parent directory is writable by the process user."

Remediation steps (one-liners):

```bash
# Create parent directory and an empty store, set ownership to current user and safe permissions
mkdir -p "$(dirname <PATH>)" && touch "<PATH>" && chown $(id -u):$(id -g) "<PATH>" && chmod 0640 "<PATH>"

# If you need group-readable or world-readable while debugging:
chmod 0644 "<PATH>"
```

After creating or fixing permissions, restart the uvicorn command.

Port-in-use conflict

- Symptom: uvicorn fails to bind the requested port and you see "Address already in use" or similar in the logs.
- Detect processes listening on the port:

```bash
# Preferred: ss
ss -ltnp | grep :<PORT>
# or lsof
lsof -iTCP -sTCP:LISTEN -P -n | grep :<PORT>
```

- Remediation: stop the conflicting process (use the PID from ss/lsof) or start uvicorn on a different port:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

VM file permission and environment notes

- Recommended file ownership for a single-VM deployment: the application process user (e.g. todoo or www-data). Use chown to set it:

```bash
sudo chown todoo:todoo "<PATH>"
```

- Recommended permission modes: directories 0755, files 0640 (or 0644 if other users need read access).

- To print the path the running process will use from code:

```bash
python -c "from app.persistence import get_data_file_path; print(get_data_file_path())"
```

If you still have issues, check persistence/README.md for more details about the JSON store and how the code resolves the path.

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
