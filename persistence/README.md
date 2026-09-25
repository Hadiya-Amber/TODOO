Persistence for TODOO
====================

This document describes the intended server-side JSON file store location and
access considerations for TODOO. It is intentionally a high-level guide to be
followed by engineers implementing durable persistence and instrumentation.

Location and path pattern
-------------------------

The runtime path for the JSON store is resolved from the environment variable
TODOO_DATA_FILE. Example patterns:

- Single file inside application data directory: /var/lib/todoo/todos.json
- Per-tenant files: /var/lib/todoo/store/<tenant-id>.json
- Local development default: ./data/todoo.json

The code scaffold in app/persistence.py resolves TODOO_DATA_FILE and falls
back to ./data/todoo.json when the variable is not set. Production deployments
should set TODOO_DATA_FILE to a directory on the VM with appropriate
permissions and durability characteristics.

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

- TODOO_DATA_FILE - Absolute or relative path to the JSON persistence file.
  Example: /var/lib/todoo/todos.json
- SECRET_KEY - Application secret (used by the app; not directly persistence
  related but documented here for convenience).

Security and operational notes
------------------------------

- Do not store secrets in files under the data directory unless they are
  encrypted and access-controlled.
- Ensure regular backups of the data directory if it contains production data.
- When adding instrumentation, avoid expensive synchronous IO on request
  paths; prefer background workers or sampling to limit impact on latency.

This README is a living document; update it when persistence semantics or the
intended file layout change.
