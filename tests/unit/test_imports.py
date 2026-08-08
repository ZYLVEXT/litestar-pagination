"""Import-boundary regressions for optional integrations."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    """Run an import assertion in a fresh interpreter.

    Returns:
        The completed child process.
    """
    return subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_isolated(code: str) -> None:
    """Assert that an isolated import script succeeds."""
    result = _run_isolated(code)
    assert result.returncode == 0, result.stdout + result.stderr


def test_root_import_keeps_sqlalchemy_adapter_lazy() -> None:
    """The stable root does not eagerly import its optional adapter."""
    _assert_isolated(
        "import sys\nimport litestar_pagination\nassert 'litestar_pagination.ext.sqlalchemy' not in sys.modules\n",
    )


def test_root_import_works_when_optional_integrations_are_unavailable() -> None:
    """A base installation remains usable when integration imports are blocked."""
    _assert_isolated(
        "import builtins\n"
        "real_import = builtins.__import__\n"
        "def guarded_import(name, *args, **kwargs):\n"
        "    if name.split('.', 1)[0] in {'sqlalchemy', 'sqlakeyset', 'advanced_alchemy'}:\n"
        "        raise ModuleNotFoundError(name)\n"
        "    return real_import(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded_import\n"
        "from litestar_pagination import CursorPage, CursorParams\n"
        "assert CursorParams().size == 50\n"
        "assert CursorPage is not None\n",
    )
