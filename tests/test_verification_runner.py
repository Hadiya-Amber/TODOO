import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Greenfield-style imports: the tests import the planned runtime/public API
# symbols at module import time. If the planned modules do not exist yet, the
# test collection will fail (RED) which is the intended behaviour for new
# tests that assert new behaviour is required by the task plan.
from client_harness.verification import run_verification
from client_harness.verify_runner import compute_median_ms_by_operation
from instrumentation.latency_placeholder import (
    clear_captured_records,
    get_captured_records,
    get_captured_diagnostics,
)
import os
from pathlib import Path as _Path

# Ensure a default data directory exists so importing the app package does not
# raise during module import-time validation. Tests will monkeypatch functions
# on app.persistence as needed for individual cases.
_default_p = _Path.cwd() / "data" / "todoo.json"
_default_p.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TODOS_JSON_PATH", str(_default_p))

import app.persistence as app_persistence


def _isoparse(v: str) -> None:
    # helper assertion that raises on bad ISO-8601
    datetime.fromisoformat(v)


def _ensure_report_keys(report: dict, keys):
    assert isinstance(report, dict), f"report must be a dict, got: {type(report)!r}"
    for k in keys:
        assert k in report, f"report missing required key: {k!r} -> {report!r}"


def test_TP_001_AC_4_1_verify_persisted_todos_after_restart(tmp_path, monkeypatch):
    """TP-001 / AC-4.1: run_verification reads persisted todos after restart and reports pass.

    Behaviour expected by the plan:
    - The verification API accepts a restart command and todos to create.
    - It verifies the persisted JSON file after simulated restart contains the created todos
      with identical id, label, done and created_at fields and returns a machine-readable
      report where report['status'] == 'pass'.
    """
    clear_captured_records()

    # Arrange: point persistence resolver at a temporary file the test controls
    data_file = tmp_path / "todos.json"
    monkeypatch.setattr(app_persistence, "get_data_file_path", lambda: str(data_file))

    todos = [{"label": "one"}, {"label": "two"}]

    # Act
    report = run_verification(["true"], todos)

    # Assert: new verification API must provide a 'status' key with 'pass' on success
    assert isinstance(report, dict), "run_verification must return a dict report"
    assert "status" in report, f"report missing 'status' key: {report!r}"
    assert report["status"] == "pass", f"expected status 'pass' but got: {report!r}"

    # The persisted file must exist and contain the created todos with required fields
    assert data_file.exists(), f"persisted file missing at {data_file}"
    parsed = json.loads(data_file.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict) and "todos" in parsed, f"persisted JSON missing top-level 'todos': {parsed!r}"
    persisted = parsed["todos"]
    assert len(persisted) == 2, f"expected 2 persisted todos, got {len(persisted)}"

    for t in persisted:
        assert all(k in t for k in ("id", "label", "done", "created_at")), f"persisted todo missing fields: {t!r}"
        # created_at must be ISO-8601 parseable
        _isoparse(t["created_at"])


def test_TP_002_AC_4_2_runner_noop_restart_and_exit_code_zero(tmp_path, monkeypatch):
    """TP-002 / AC-4.2: configured with a no-op restart command the runner verifies persisted todo equality and reports exit 0.

    The plan describes that the runner emits an exit code; the updated API is
    expected to include an exit_code field in the machine-readable report. This
    test asserts that behaviour is present and zero on success.
    """
    clear_captured_records()

    data_file = tmp_path / "todos.json"
    monkeypatch.setattr(app_persistence, "get_data_file_path", lambda: str(data_file))

    todos = [{"label": "persistent"}]

    report = run_verification(["true"], todos)

    assert isinstance(report, dict), "run_verification must return a dict report"
    assert report.get("status") == "pass", f"expected status 'pass', got: {report!r}"

    # The plan expects an explicit exit code in the machine-readable output
    assert "exit_code" in report, f"report must include 'exit_code' per AC-4.2: {report!r}"
    assert int(report["exit_code"]) == 0, f"expected exit_code 0 for pass, got: {report['exit_code']!r}"


def test_TP_003_AC_5_1_compute_median_latency_for_create_is_200ms():
    """TP-003 / AC-5.1: median computation for 'create' samples [100,200,300] ms -> 200 ms.

    The planned verify_runner module exposes a function that computes per-operation
    median latencies in milliseconds from captured records. This test asserts
    that the median is computed as 200 (ms) for the provided samples.
    """
    clear_captured_records()

    now = datetime.now(timezone.utc).isoformat()
    sample_records = [
        {"timestamp": now, "operation": "create", "elapsed_s": 0.100},
        {"timestamp": now, "operation": "create", "elapsed_s": 0.200},
        {"timestamp": now, "operation": "create", "elapsed_s": 0.300},
    ]

    medians = compute_median_ms_by_operation(sample_records)
    assert isinstance(medians, dict), f"median computation must return dict, got: {medians!r}"

    create_ms = medians.get("create")
    assert create_ms is not None, f"no 'create' median in {medians!r}"
    rounded = int(round(float(create_ms)))
    assert rounded == 200, f"expected median 200 ms for create, got {create_ms!r} (rounded {rounded})"


def test_TP_004_AC_5_2_runner_flags_failure_when_edit_median_exceeds_500ms(monkeypatch, tmp_path):
    """TP-004 / AC-5.2: runner fails verification when 'edit' median is 600ms and includes latency breakdown.
    """
    clear_captured_records()

    # Prepare synthetic captured instrumentation where edit median = 600ms
    now = datetime.now(timezone.utc).isoformat()
    sample = [
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.500},
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.600},
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.700},
    ]

    # Replace the instrumentation source read by the runner
    monkeypatch.setattr(
        "instrumentation.latency_placeholder.get_captured_records",
        lambda: list(sample),
    )

    # Ensure persistence path is harmless
    p = tmp_path / "todos.json"
    monkeypatch.setenv("PERSISTENCE_PATH", str(p))

    report = run_verification(["true"], [])
    assert isinstance(report, dict), "run_verification must return a dict report"

    assert report.get("status") == "fail", f"expected status 'fail' for high edit median, got: {report!r}"

    latencies = report.get("latencies")
    assert isinstance(latencies, dict) and "edit" in latencies, f"report must include latencies.edit: {report!r}"
    assert float(latencies["edit"]) >= 600, f"expected edit median >= 600 ms, got {latencies['edit']!r}"

    diagnostics = report.get("diagnostics")
    assert diagnostics is not None, f"report must include 'diagnostics' explaining failure: {report!r}"
    diag_text = json.dumps(diagnostics)
    assert "latency" in diag_text.lower() or "threshold" in diag_text.lower(), (
        f"diagnostics should reference latency threshold breach: {diagnostics!r}"
    )


def test_TP_005_AC_6_1_runner_reports_permission_error_when_load_store_raises_OSError(monkeypatch):
    """TP-005 / AC-6.1: when load_store raises PermissionError/OSError(13) runner produces failing report with errno details.
    """
    clear_captured_records()

    # Replace load_store with one that raises permission error
    def _raiser():
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(app_persistence, "load_store", lambda: (_ for _ in ()).throw(OSError(13, "Permission denied")))

    report = run_verification(["true"], [])
    assert isinstance(report, dict), "run_verification must return a dict report"

    assert report.get("status") == "fail", f"expected status 'fail' when persistence load fails: {report!r}"

    # Look for permission details in persistence errors or diagnostics
    persistence_section = report.get("persistence") if isinstance(report.get("persistence"), dict) else {}
    errors = persistence_section.get("errors") if persistence_section else report.get("errors")
    errors_text = json.dumps(errors)
    assert "Permission denied" in errors_text or "Errno 13" in errors_text or "13" in errors_text, (
        f"report must surface errno 13 and 'Permission denied' in persistence errors: {errors!r}"
    )


def test_TP_006_AC_6_2_runner_reports_parse_error_for_invalid_json(tmp_path, monkeypatch):
    """TP-006 / AC-6.2: when persistence file contains invalid JSON the runner produces a failing report with parse diagnostics.
    """
    clear_captured_records()

    data_file = tmp_path / "todos.json"
    data_file.write_bytes(b"}{ notjson")
    monkeypatch.setattr(app_persistence, "get_data_file_path", lambda: str(data_file))

    report = run_verification(["true"], [])
    assert isinstance(report, dict), "run_verification must return a dict report"

    assert report.get("status") == "fail", f"expected status 'fail' for parse error, got: {report!r}"

    diagnostics = report.get("diagnostics") or get_captured_diagnostics()
    diag_text = json.dumps(diagnostics)
    assert "parse" in diag_text.lower() or "json" in diag_text.lower() or "decode" in diag_text.lower(), (
        f"expected parse diagnostic in report diagnostics: {diagnostics!r}"
    )


def test_TP_007_AC_7_1_runner_emits_single_report_json_and_pass_on_good_latencies(tmp_path, monkeypatch):
    """TP-007 / AC-7.1: run_verification emits a single machine-readable report with expected keys and passes when medians under threshold.
    """
    clear_captured_records()

    # Prepare instrumentation with medians under 500ms for create
    now = datetime.now(timezone.utc).isoformat()
    sample = [
        {"timestamp": now, "operation": "create", "elapsed_s": 0.050},
        {"timestamp": now, "operation": "create", "elapsed_s": 0.150},
        {"timestamp": now, "operation": "create", "elapsed_s": 0.250},
    ]
    monkeypatch.setattr(
        "instrumentation.latency_placeholder.get_captured_records",
        lambda: list(sample),
    )

    # Prepare a persisted todos file that matches created todos
    data_file = tmp_path / "todos.json"
    created_todos = [
        {"id": 1, "label": "one", "done": False, "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    data_file.write_text(json.dumps({"todos": created_todos}), encoding="utf-8")
    monkeypatch.setattr(app_persistence, "get_data_file_path", lambda: str(data_file))

    report = run_verification(["true"], [])
    assert isinstance(report, dict), "run_verification must return a dict report"

    # Required keys per AC-7
    _ensure_report_keys(report, ["status", "latencies", "persistence", "diagnostics"])
    assert report["status"] == "pass", f"expected status 'pass' but got: {report!r}"

    # Assert median value for create equals expected (rounded ms)
    create_ms = report["latencies"].get("create")
    assert create_ms is not None, f"report.latencies must include 'create': {report!r}"
    assert int(round(float(create_ms))) == 150, f"expected create median ~150ms, got {create_ms!r}"


def test_TP_008_AC_7_2_runner_fails_when_edit_median_exceeds_threshold_and_reports_diagnostics(monkeypatch, tmp_path):
    """TP-008 / AC-7.2: runner fails when edit median >= 600ms and diagnostics reference threshold breach.
    """
    clear_captured_records()

    now = datetime.now(timezone.utc).isoformat()
    sample = [
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.580},
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.600},
        {"timestamp": now, "operation": "edit", "elapsed_s": 0.620},
    ]
    monkeypatch.setattr(
        "instrumentation.latency_placeholder.get_captured_records",
        lambda: list(sample),
    )

    # harmless persistence
    p = tmp_path / "todos.json"
    monkeypatch.setenv("PERSISTENCE_PATH", str(p))

    report = run_verification(["true"], [])
    assert isinstance(report, dict), "run_verification must return a dict report"

    assert report.get("status") == "fail", f"expected status 'fail' when edit median >= 600ms, got: {report!r}"
    latencies = report.get("latencies") or {}
    assert float(latencies.get("edit", 0)) >= 600, f"expected edit median >= 600, got: {latencies.get('edit')!r}"

    diagnostics = report.get("diagnostics")
    diag_text = json.dumps(diagnostics)
    assert "latency" in diag_text.lower() or "threshold" in diag_text.lower() or "edit" in diag_text.lower(), (
        f"diagnostics should reference latency threshold breach: {diagnostics!r}"
    )
