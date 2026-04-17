import os

import pytest

from trashdig.utils import clear_binary_stubs


@pytest.fixture(autouse=True)
def setup_test_env(request):
    """Ensure binary stubs are cleared and sandbox can be skipped for tests."""
    old_val = os.environ.get("TRASHDIG_SKIP_SANDBOX")
    # Don't skip sandbox for tests that specifically test sandbox behaviour
    is_sandbox_test = "test_sandbox" in request.fspath.basename
    if not is_sandbox_test:
        os.environ["TRASHDIG_SKIP_SANDBOX"] = "1"
    yield
    clear_binary_stubs()
    if old_val is not None:
        os.environ["TRASHDIG_SKIP_SANDBOX"] = old_val
    elif "TRASHDIG_SKIP_SANDBOX" in os.environ:
        del os.environ["TRASHDIG_SKIP_SANDBOX"]
