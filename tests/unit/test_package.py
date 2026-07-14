"""Package metadata tests."""

import pytest

import litestar_pagination

pytestmark = pytest.mark.unit


def test_version() -> None:
    """Expose the package version."""
    assert litestar_pagination.__version__ == "0.1.0"
