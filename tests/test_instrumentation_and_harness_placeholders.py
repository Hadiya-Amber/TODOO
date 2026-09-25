from pathlib import Path


def test_placeholders_and_persistence_readme_contains_env_and_paths():
    """TP-002: Assert instrumentation and client harness placeholders exist and are documented.

    This test checks for the presence of:
      - instrumentation/latency_placeholder.py
      - client_harness/README.md

    and then verifies that persistence/README.md contains:
      - a reference to environment documentation (checks for the word 'environment')
      - the placeholder paths for instrumentation and the client harness

    Each file existence check is asserted first so missing files fail by assertion.
    """
    root = Path.cwd()

    instr_placeholder = root / "instrumentation" / "latency_placeholder.py"
    client_harness_readme = root / "client_harness" / "README.md"
    persistence_readme = root / "persistence" / "README.md"

    assert instr_placeholder.is_file(), (
        f"Expected instrumentation placeholder at {instr_placeholder}"
    )
    assert client_harness_readme.is_file(), (
        f"Expected client harness README at {client_harness_readme}"
    )

    assert persistence_readme.is_file(), (
        f"Expected persistence/README.md to exist at {persistence_readme}"
    )

    content = persistence_readme.read_text(encoding="utf-8").lower()

    # Check that the README talks about environment configuration in some form.
    assert "environment" in content or "env" in content, (
        "Expected persistence/README.md to mention environment configuration or environment variables"
    )

    # Check that the README references the instrumentation placeholder path and client harness path.
    assert "instrumentation/latency_placeholder.py" in content, (
        "Expected persistence/README.md to reference instrumentation/latency_placeholder.py"
    )
    # README content is lowercased for matching, so match the lowercase path.
    assert "client_harness/readme.md" in content, (
        "Expected persistence/README.md to reference client_harness/README.md"
    )
