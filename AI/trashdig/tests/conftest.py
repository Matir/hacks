import os

import pytest

from trashdig.utils import clear_binary_stubs


@pytest.fixture(autouse=True)
def setup_test_env():
    """Ensure binary stubs are cleared and sandbox can be skipped for tests."""
    old_val = os.environ.get("TRASHDIG_SKIP_SANDBOX")
    os.environ["TRASHDIG_SKIP_SANDBOX"] = "1"
    yield
    clear_binary_stubs()
    if old_val is not None:
        os.environ["TRASHDIG_SKIP_SANDBOX"] = old_val
    else:
        del os.environ["TRASHDIG_SKIP_SANDBOX"]
