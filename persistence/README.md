Persistence for TODOO
====================

This document describes the intended server-side JSON file store location and
access considerations for TODOO. It is intentionally a high-level guide to be
followed by engineers implementing durable persistence and instrumentation.

Location and path pattern
-------------------------

The runtime path for the JSON store is resolved from the environment variable
TODOS_JSON_PATH. Example patterns:

- Single file inside application data directory: /var/lib/todoo/todos.json
- Per-tenant files: /var/lib/todoo/store/<tenant-id>.json
- Local development default: ./data/todoo.json

The code scaffold in app/persistence.py resolves TODOS_JSON_PATH and falls
back to ./data/todoo.json when the variable is not set. Production
deployments should set TODOS_JSON_PATH to a directory on the VM with
appropriate permissions and durability characteristics.

Permissions and access
----------------------

- Ownership: the process user (for example, `todoo` or `www-data`) should own
  the data directory and files to avoid permission issues during runtime.
- Mode: data directories may be created with 0755 and files with 0640 or
  0644 depending on whether other system users need read access.
- Backups: consider mounting the data directory on a persistent volume or
  configuring regular backups; file-based stores are not resilient to VM
  replacement without external backups.

Durability expectations
-----------------------

This project uses a simple file-based JSON store as a development-friendly
persistence mechanism. The basic implementation is best-effort and does not
provide atomic replace or fsync guarantees. For production use:

- Implement atomic writes (write-to-temp then atomic rename) to avoid
  partially-written files.
- Call fsync on the file descriptor and its parent directory if strong
  durability is required.
- Consider migrating to a real database if concurrency and durability
  requirements grow beyond what file-based storage can provide.

Instrumentation and latency hooks
--------------------------------

Runtime latency measurement and instrumentation hooks should be added inside
the instrumentation/ directory. A placeholder module exists at
instrumentation/latency_placeholder.py and is the intended location for
instrumentation initialization and per-operation latency recording calls.

Client-side latency harness
---------------------------

The client-side harness used to exercise endpoints and measure latency will
live under client_harness/. A placeholder README exists at
client_harness/README.md describing the intended harness shape. CI can add
jobs that invoke the harness to perform latency gating in the future.

Environment variables
---------------------

- TODOS_JSON_PATH - Absolute or relative path to the JSON persistence file.
  Example: /var/lib/todoo/todos.json
- SECRET_KEY - Application secret (used by the app; not directly persistence
  related but documented here for convenience).

Verifying the runtime JSON store path and permissions
----------------------------------------------------

The authoritative source of the runtime JSON store path is the application
code: app/persistence.py::get_data_file_path(). Use the following commands to
verify the path your running process will use and to inspect filesystem
permissions. These commands are safe to run from your development account.

- Print the resolved path from the shell:

```bash
python -c "from app.persistence import get_data_file_path; print(get_data_file_path())"
```

- Check the file and directory listing and permissions (replace <path> with
  the printed path above):

```bash
ls -ld "$(dirname <path>)" && ls -l <path> || true
```

- Alternatively use stat for a more detailed view:

```bash
stat <path>
```

Common startup errors and exact messages
---------------------------------------

When the persistence file or its parent directory is missing or unwritable,
the application may fail during startup. The code uses validate_data_file and
file I/O that can raise standard Python exceptions. Examples you may see in the
server logs or traceback include:

- FileNotFoundError: [Errno 2] No such file or directory: '<path>'
- PermissionError: [Errno 13] Permission denied: '<path>'
- RuntimeError raised by the persistence resolver with exact messages such as:

  - "persistence: parent directory for JSON store does not exist: <path>\nRemediation: create the parent directory or change TODOS_JSON_PATH to a writable location."

  - "persistence: configured JSON store is not writable: <path>\nRemediation: adjust file permissions or ownership so the process can write to the file."

  - "persistence: unable to create initial JSON store at <path>: <os error>\nRemediation: ensure the parent directory is writable by the process user."

Use the exact message text above to match log lines when troubleshooting. The authoritative resolvers are documented in code: app/persistence.py::get_data_file_path() and app/persistence.py::validate_data_file().

Remediation: create the path, set ownership and safe permissions (one-liner)

```bash
# Create parent directory, empty file, set ownership to current user and safe permissions
mkdir -p "$(dirname <PATH>)" && touch "<PATH>" && chown $(id -u):$(id -g) "<PATH>" && chmod 0640 "<PATH>"

# If you need group-readable or world-readable while debugging:
chmod 0644 "<PATH>"
```

Recommended ownership and modes for a single-VM deployment
-----------------------------------------------------------

- Directories: 0755
- Files: 0640 (or 0644 if other system users need read access)
- Ownership: the application process user (for example, `todoo` or `www-data`)

If you prefer to initialise the store from Python (safe and idempotent):

```bash
python -c "from app.persistence import save_store; save_store([])"
```

Cross-reference: foreground startup and uvicorn examples
-------------------------------------------------------

See the repository README's "Local runtime / VM startup" section for one-line
uvicorn examples, environment variable usage (TODOS_JSON_PATH), and sample
curl commands that exercise create, edit, toggle and delete flows.

Example foreground startup
--------------------------

The tests and local development can run the FastAPI application in the
foreground without uvicorn using a simple Python module invocation. Set the
TODOS_JSON_PATH environment variable and run the module. The module supports
optional --host and --port flags; when omitted it defaults to --host 127.0.0.1
and --port 8000 (the defaults the test harness expects).

```bash
# Example: run in foreground binding to localhost:8000 (default test host/port)
TODOS_JSON_PATH=/tmp/todos.json python -m app --host 127.0.0.1 --port 8000

# Equivalent explicit module path calling the package initializer:
TODOS_JSON_PATH=/tmp/todos.json python -m app.__init__ --host 127.0.0.1 --port 8000

# You can also bind to all interfaces if desired:
# TODOS_JSON_PATH=/tmp/todos.json python -m app --host 0.0.0.0 --port 8000
```

Alternatively, use uvicorn as documented in the repository README if available:

```bash
TODOS_JSON_PATH=/tmp/todos.json uvicorn app:app --host 127.0.0.1 --port 8000
```

Cross-reference: see the repository README 'Local development' troubleshooting
section for guidance on diagnosing permission denied errors when running the
application locally.

Security and operational notes
------------------------------

- Do not store secrets in files under the data directory unless they are
  encrypted and access-controlled.
- Ensure regular backups of the data directory if it contains production data.
- When adding instrumentation, avoid expensive synchronous IO on request
  paths; prefer background workers or sampling to limit impact on latency.

This README is a living document; update it when persistence semantics or the
intended file layout change.
