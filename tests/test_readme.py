'''
Tests asserting the presence of developer-facing repository artifacts.

These tests are intentionally strict and failing (RED) when the
expected scaffold markers are not present so the repository owner
is guided to add them.

Note: AC-6 (CI runtime behavior with missing secrets) cannot be reliably
unit-tested inside this test run; it should be validated inside CI. This
module documents that constraint but does not attempt to exercise secrets
or CI runtime behavior.
'''

from pathlib import Path
import re


def test_readme_contains_developer_markers():
    """AC-1 / AC-3 / AC-4: README.md exists and documents checkout, install,
    environment variables, a one-line run command, and a repo layout mentioning
    FastAPI, tests/, instrumentation/metrics, and client/web.
    """
    readme = Path("README.md")
    assert readme.exists(), "README.md not found at repository root"

    content = readme.read_text(encoding="utf8")
    lower = content.lower()

    # Top-level Markdown heading (a line starting with '# ')
    assert re.search(r'(?m)^#\s+', content), "README.md must contain a top-level Markdown heading (a line starting with '# ')"

    # Checkout instructions
    assert 'git clone' in lower, "README.md should include 'git clone' checkout instructions"

    # Install instructions: either specific requirements.in usage or at least 'pip install'
    assert ('pip install -r requirements.in' in lower) or ('pip install' in lower), (
        "README.md should include install instructions ('pip install -r requirements.in' or at least 'pip install')"
    )

    # Required environment variables: look for explicit phrasing or the token 'env'
    env_marker = (
        ('environment variable' in lower)
        or ('environment variables' in lower)
        or re.search(r'\benv\b', lower)
        or ('env:' in lower)
    )
    assert env_marker, "README.md should mention required environment variables (e.g. 'environment variable' or 'ENV')"

    # One-line run command placeholder referencing uvicorn, python -m, or 'run'
    run_marker = ('uvicorn' in lower) or ('python -m' in lower) or re.search(r'\brun\b', lower)
    assert run_marker, "README.md should contain a one-line run command placeholder referencing 'uvicorn', 'python -m', or 'run'"

    # Repository layout expectations
    assert 'fastapi' in lower, "README.md should mention 'FastAPI' in the repository layout"
    assert 'tests/' in content or 'tests/' in lower, "README.md should mention the 'tests/' directory in the layout"
    assert ('instrumentation' in lower) or ('metrics' in lower), "README.md should mention 'instrumentation' or 'metrics' in the layout"
    assert ('client' in lower) or ('web' in lower), "README.md should mention 'client' or 'web' in the layout"


def test_ci_workflow_contains_pytest_and_latency_gating():
    """AC-2 / AC-5: CI workflow file exists and invokes the test command and
    contains a clearly marked placeholder/job slot for 'latency-gating'.
    """
    ci = Path('.github/workflows/ci.yml')
    assert ci.exists(), ".github/workflows/ci.yml not found"

    content = ci.read_text(encoding='utf8')
    lower = content.lower()

    # CI must invoke the test runner with the expected command
    assert 'python -m pytest -q' in content or 'python -m pytest -q' in lower, (
        "CI workflow should invoke tests with 'python -m pytest -q'"
    )

    # Placeholder for latency-gating job
    assert 'latency-gating' in lower, "CI workflow should contain a placeholder or job slot labeled 'latency-gating'"
