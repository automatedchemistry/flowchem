import sys
from pathlib import Path

import pytest
from xprocess import ProcessStarter


@pytest.fixture(scope="module")
def flowchem_test_instance(xprocess):
    """
    Pytest fixture to set up and tear down a FlowChem instance for testing.

    This fixture uses the xprocess plugin to start a FlowChem instance before any tests
    in the module run and ensures it is terminated after all tests complete. The fixture
    expects a configuration file named 'test_config.toml' in the same directory as the
    test script and the main FlowChem script to be located at '../src/flowchem/__main__.py'
    relative to the test script.

    Args:
        xprocess: The pytest-xprocess fixture, used to manage external processes.

    Yields:
        None. The fixture sets up the FlowChem instance before tests and tears it down after tests.

    Raises:
        TimeoutError: If the FlowChem instance does not start within the specified timeout.
    """
    config_file = Path(__file__).parent.resolve() / "test_config.toml"
    main = Path(__file__).parent.resolve() / ".." / "src" / "flowchem" / "__main__.py"

    class Starter(ProcessStarter):
        # Process startup ends with this text in stdout (timeout is long cause some GA runners are slow)
        pattern = "Uvicorn running"
        timeout = 30

        # execute flowchem with current venv
        args = [sys.executable, main, config_file]

    xprocess.ensure("flowchem_instance", Starter)
    yield
    xprocess.getinfo("flowchem_instance").terminate()
