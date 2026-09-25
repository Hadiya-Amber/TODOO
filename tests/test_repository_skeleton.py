from pathlib import Path


def test_repository_files_exist():
    """TP-001: Assert that core package and persistence README files exist.

    This test checks for the presence of:
      - app/__init__.py
      - app/persistence.py
      - persistence/README.md

    The assertions are simple filesystem checks so that when the
    scaffold is not yet present the test fails by assertion (RED).
    """
    root = Path.cwd()

    app_init = root / "app" / "__init__.py"
    app_persistence = root / "app" / "persistence.py"
    persistence_readme = root / "persistence" / "README.md"

    assert app_init.is_file(), f"Expected file app/__init__.py to exist at {app_init}"
    assert app_persistence.is_file(), f"Expected file app/persistence.py to exist at {app_persistence}"
    assert persistence_readme.is_file(), (
        f"Expected file persistence/README.md to exist at {persistence_readme}"
    )
