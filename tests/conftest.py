"""
Pytest Configuration with pytest-xdist Parallelization Support.

This module provides:
1. Thread-safe fixtures for parallel test execution
2. Worker-scoped fixtures for resource isolation
3. Hooks for pytest-xdist parallelization
4. Configuration integration with QA-FRAMEWORK config files
5. Advanced test patterns (AAA, BDD, Factories, Builders)

Usage:
    pytest -n auto              # Auto-detect number of workers
    pytest -n 4                 # Use 4 workers
    pytest -n logical           # Use logical CPU count
    pytest --dist=loadfile      # Distribute by file
    pytest --dist=loadscope     # Distribute by scope

Clean Architecture: Infrastructure layer (pytest configuration)
SOLID Principles:
    - SRP: Each fixture has a single responsibility
    - OCP: Extensible through hooks
    - DIP: Depends on ConfigManager abstraction
"""

import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Generator, List, Optional

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.infrastructure.config.config_manager import ConfigManager, QAConfig
from src.infrastructure.logger.logger import QALogger

# Import advanced fixtures
pytest_plugins = [
    "tests.fixtures.advanced_fixtures",
    "tests.fixtures.adapters",
    "tests.fixtures.contract_fixtures",
    "tests.fixtures.langfuse_fixtures",
]

# =============================================================================
# GLOBAL STATE FOR PARALLEL EXECUTION
# =============================================================================

# Thread-safe data structures for parallel execution
_worker_locks: Dict[str, threading.Lock] = {}
_resource_pools: Dict[str, Queue] = {}
_test_data: Dict[str, Any] = {}
_data_lock = threading.Lock()

# Worker identification
_worker_id: Optional[str] = None
_session_id: Optional[str] = None


def get_worker_id() -> str:
    """
    Get the current worker ID.

    Returns:
        Worker identifier or 'master' if not running in parallel mode.
    """
    global _worker_id
    if _worker_id is not None:
        return _worker_id

    # Check if running under pytest-xdist
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker:
        _worker_id = worker
    else:
        _worker_id = "master"

    return _worker_id


def get_session_id() -> str:
    """
    Get the current test session ID.

    Returns:
        Session identifier for this test run.
    """
    global _session_id
    if _session_id is None:
        _session_id = str(uuid.uuid4())[:8]
    return _session_id


# =============================================================================
# PYTEST HOOKS FOR PARALLELIZATION
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure pytest with xdist settings.

    Args:
        config: Pytest configuration object.
    """
    # Register custom markers for parallel execution
    config.addinivalue_line("markers", "parallel_safe: mark test as safe for parallel execution")
    config.addinivalue_line("markers", "serial: mark test to run serially (not in parallel)")
    config.addinivalue_line("markers", "worker_id(name): mark test to run on specific worker")
    config.addinivalue_line("markers", "isolated: mark test that requires complete isolation")

    # Store parallel configuration
    config.parallel_workers = config.getoption("numprocesses", default=None)
    config.parallel_dist = config.getoption("dist", default="no")


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Called after the Session object has been created.

    Args:
        session: Pytest session object.
    """
    # Initialize session-scoped resources
    worker_id = get_worker_id()
    session_id = get_session_id()

    # Log session start
    print(f"\n[Session {session_id}] Started on worker: {worker_id}")

    # Initialize worker-specific resources
    with _data_lock:
        if worker_id not in _worker_locks:
            _worker_locks[worker_id] = threading.Lock()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Called after whole test run finished.

    Args:
        session: Pytest session object.
        exitstatus: Exit status of the test run.
    """
    worker_id = get_worker_id()
    session_id = get_session_id()

    print(f"\n[Session {session_id}] Finished on worker: {worker_id} (exit: {exitstatus})")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Called before each test setup.

    Args:
        item: Pytest test item.
    """
    # Check if test is marked as serial
    if item.get_closest_marker("serial"):
        # Ensure serial execution by checking active workers
        pass  # Handled by --dist=loadscope

    # Log test start on worker
    worker_id = get_worker_id()
    print(f"  [Worker {worker_id}] Running: {item.nodeid}")


# =============================================================================
# CONFIGURATION FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def qa_config() -> QAConfig:
    """
    Load QA-FRAMEWORK configuration.

    Returns:
        QAConfig instance with loaded configuration.

    Example:
        def test_example(qa_config):
            assert qa_config.test.timeout == 30
    """
    config_manager = ConfigManager()
    return config_manager.get_config()


@pytest.fixture(scope="session")
def parallel_workers(qa_config: QAConfig) -> int:
    """
    Get number of parallel workers from configuration.

    Args:
        qa_config: QA configuration fixture.

    Returns:
        Number of parallel workers configured.
    """
    return qa_config.test.parallel_workers


@pytest.fixture(scope="session")
def test_environment(qa_config: QAConfig) -> str:
    """
    Get test environment from configuration.

    Args:
        qa_config: QA configuration fixture.

    Returns:
        Current test environment (development, staging, production).
    """
    return qa_config.test.environment


# =============================================================================
# THREAD-SAFE RESOURCE FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def resource_lock() -> Generator[threading.Lock, None, None]:
    """
    Provide a thread-safe lock for resource synchronization.

    Yields:
        threading.Lock instance unique to the current worker.

    Example:
        def test_with_shared_resource(resource_lock):
            with resource_lock:
                # Critical section - only one test at a time
                shared_resource.modify()
    """
    worker_id = get_worker_id()

    with _data_lock:
        if worker_id not in _worker_locks:
            _worker_locks[worker_id] = threading.Lock()

    yield _worker_locks[worker_id]


@pytest.fixture(scope="session")
def shared_queue() -> Queue:
    """
    Provide a thread-safe queue for inter-test communication.

    Returns:
        Queue instance for safe data sharing between tests.

    Example:
        def test_producer(shared_queue):
            shared_queue.put("data")

        def test_consumer(shared_queue):
            data = shared_queue.get()
    """
    worker_id = get_worker_id()

    with _data_lock:
        if worker_id not in _resource_pools:
            _resource_pools[worker_id] = Queue()

    return _resource_pools[worker_id]


@pytest.fixture(scope="session")
def worker_id() -> str:
    """
    Get current worker identifier.

    Returns:
        Worker ID string (e.g., 'gw0', 'gw1', or 'master').

    Example:
        def test_worker_isolation(worker_id):
            assert worker_id.startswith("gw") or worker_id == "master"
    """
    return get_worker_id()


@pytest.fixture(scope="session")
def session_id() -> str:
    """
    Get current test session identifier.

    Returns:
        Session ID string unique to this test run.

    Example:
        def test_session_id(session_id):
            assert len(session_id) == 8
    """
    return get_session_id()


@pytest.fixture(scope="session")
def worker_temp_dir(tmp_path_factory: pytest.TempPathFactory, worker_id: str) -> Path:
    """
    Provide a temporary directory isolated per worker.

    Args:
        tmp_path_factory: Pytest temp path factory.
        worker_id: Current worker identifier.

    Returns:
        Path to worker-isolated temporary directory.

    Example:
        def test_with_temp_file(worker_temp_dir):
            temp_file = worker_temp_dir / "test.txt"
            temp_file.write_text("data")
    """
    return tmp_path_factory.mktemp(f"worker_{worker_id}")


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def isolated_test_data(worker_id: str) -> Dict[str, Any]:
    """
    Provide isolated test data dictionary per test.

    Args:
        worker_id: Current worker identifier.

    Yields:
        Dictionary for test data storage.

    Example:
        def test_data_isolation(isolated_test_data):
            isolated_test_data["key"] = "value"
            assert isolated_test_data["key"] == "value"
    """
    test_id = str(uuid.uuid4())[:8]
    data_key = f"{worker_id}_{test_id}"

    with _data_lock:
        _test_data[data_key] = {}

    try:
        yield _test_data[data_key]
    finally:
        with _data_lock:
            if data_key in _test_data:
                del _test_data[data_key]


@pytest.fixture(scope="session")
def faker_factory(worker_id: str) -> Generator[Any, None, None]:
    """
    Provide a thread-safe Faker instance per worker.

    Args:
        worker_id: Current worker identifier.

    Yields:
        Faker instance configured for this worker.

    Example:
        def test_with_fake_data(faker_factory):
            name = faker_factory.name()
            email = faker_factory.email()
    """
    from faker import Faker

    # Create Faker instance with worker-specific seed
    fake = Faker()
    fake.seed_instance(hash(worker_id) % 10000)

    yield fake


# =============================================================================
# UTILITY FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def timer() -> Generator[Dict[str, float], None, None]:
    """
    Provide a timer fixture for performance measurements.

    Yields:
        Dictionary with timing information.

    Example:
        def test_performance(timer):
            timer["start"] = time.time()
            # ... test logic ...
            timer["end"] = time.time()
            elapsed = timer["end"] - timer["start"]
            assert elapsed < 1.0
    """
    timing_data: Dict[str, float] = {}
    timing_data["start"] = time.time()

    yield timing_data

    timing_data["end"] = time.time()
    timing_data["elapsed"] = timing_data["end"] - timing_data["start"]


@pytest.fixture(scope="function")
def execution_context(worker_id: str, session_id: str) -> Dict[str, Any]:
    """
    Provide execution context information for tests.

    Args:
        worker_id: Current worker identifier.
        session_id: Current session identifier.

    Returns:
        Dictionary with execution context.

    Example:
        def test_with_context(execution_context):
            assert "worker_id" in execution_context
            assert "session_id" in execution_context
            assert "timestamp" in execution_context
    """
    return {
        "worker_id": worker_id,
        "session_id": session_id,
        "timestamp": time.time(),
        "process_id": os.getpid(),
        "thread_id": threading.current_thread().ident,
    }


# =============================================================================
# CONTEXT MANAGERS FOR PARALLEL TESTING
# =============================================================================


@contextmanager
def worker_isolation(worker_id: str) -> Generator[None, None, None]:
    """
    Context manager for complete test isolation.

    Args:
        worker_id: Current worker identifier.

    Example:
        with worker_isolation("gw0"):
            # Code running in isolation
            pass
    """
    # Acquire worker-specific lock
    with _data_lock:
        if worker_id not in _worker_locks:
            _worker_locks[worker_id] = threading.Lock()

    with _worker_locks[worker_id]:
        yield


@contextmanager
def synchronized_section(lock_name: str) -> Generator[None, None, None]:
    """
    Context manager for named synchronized sections.

    Args:
        lock_name: Name of the lock to use.

    Example:
        with synchronized_section("database"):
            # Only one test can access this section at a time
            pass
    """
    with _data_lock:
        if lock_name not in _worker_locks:
            _worker_locks[lock_name] = threading.Lock()

    with _worker_locks[lock_name]:
        yield


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================


def pytest_unconfigure(config: pytest.Config) -> None:
    """
    Called before test process is exited.

    Args:
        config: Pytest configuration object.
    """
    # Cleanup global resources
    global _worker_locks, _resource_pools, _test_data

    with _data_lock:
        _worker_locks.clear()
        _resource_pools.clear()
        _test_data.clear()
