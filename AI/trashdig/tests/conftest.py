import os

import pytest

from trashdig.sandbox.landlock_tool import init_sandbox_mp_context
from trashdig.services.session import init_session_service
from trashdig.utils import clear_binary_stubs


@pytest.fixture(scope="session", autouse=True)
def init_session_service_fixture(tmp_path_factory):
    """Initialise the global SessionService for the test session."""
    tmp_dir = tmp_path_factory.mktemp("trashdig_test_data")
    db_path = str(tmp_dir / "trashdig_test.db")
    init_session_service(db_path)


@pytest.fixture(scope="session", autouse=True)
def init_landlock_spawn_context():
    """Switch the landlock sandbox to the 'spawn' start method for the test session.

    Using 'spawn' avoids needing a live forkserver and provides a clean
    Python interpreter for each sandboxed child, which is correct and safe
    for tests (albeit slightly slower than 'forkserver').
    """
    init_sandbox_mp_context("spawn")


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
