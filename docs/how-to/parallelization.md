# QA-FRAMEWORK - Parallel Testing Guide

**Autor:** Alfred  
**Fecha:** 2026-02-11 17:25 UTC

---

## 🚀 Overview

This guide explains how to use parallel test execution with pytest-xdist in QA-FRAMEWORK.

## 📊 Benefits of Parallel Testing

- **Faster execution:** Tests run simultaneously on multiple CPU cores
- **Better resource utilization:** Full use of available CPU
- **Reduced total time:** Instead of sequential execution, run tests in parallel
- **Scalability:** Easy to scale from 1 worker to N workers

---

## 🎯 How It Works

### Worker Isolation

Each worker process runs in its own Python interpreter with isolated:

- **Memory:** Separate memory space
- **Resources:** Independent file handles, database connections
- **Fixtures:** Thread-safe fixtures prevent conflicts
- **Configuration:** Worker-specific temporary directories

### Synchronization Mechanisms

QA-FRAMEWORK provides:

1. **Thread-safe locks** - Only one test can access critical sections
2. **Worker-scoped queues** - Inter-test communication
3. **Session-scoped data** - Data isolated per test run
4. **Resource pools** - Reusable resources per worker

---

## 📋 Configuration

### 1. pytest Configuration (Automatic)

The framework is pre-configured in `pyproject.toml`:

```toml
[tool.pytest-xdist]
numprocesses = "auto"  # Auto-detect CPU cores
distloadscope = "load"   # Load tests from file
```

### 2. Environment Variables

```bash
# Set specific number of workers
PYTEST_XDIST_WORKER_COUNT=4 pytest

# Use logical CPU count
PYTEST_XDIST_WORKER_COUNT=logical pytest

# Use load-scope distribution
PYTEST_XDIST_DIST_LOAD_SCOPE=loadfile pytest
```

### 3. QA Framework Config

In `config/qa.yaml`:

```yaml
test:
  environment: development
  parallel_workers: auto  # auto, 1, 2, 4, 8, logical
  timeout: 30
  retry_failed: 0
```

---

## 🚀 Running Tests in Parallel

### Command Examples

```bash
# Auto-detect number of workers
pytest

# Use 4 workers
pytest -n 4

# Use all available CPU cores
pytest -n auto

# Use logical CPU count
pytest -n logical

# Distribute by load scope
pytest --dist=loadscope

# Use custom loadfile
pytest --dist=loadfile --distloadscope=tests/parallel/loadfile.txt

# Combine parallel execution with coverage
pytest -n 4 --cov=src --cov-report=html
```

### Run Specific Test Files

```bash
# Run API tests in parallel
pytest tests/api/ -n auto

# Run UI tests in parallel
pytest tests/ui/ -n auto -m ui

# Run specific test
pytest tests/test_example.py::test_example -n 2
```

---

## 🧩 Thread-Safe Fixtures

QA-FRAMEWORK provides several thread-safe fixtures:

### resource_lock()

Ensure only one test accesses critical resources at a time:

```python
def test_shared_resource(resource_lock):
    with resource_lock:
        # Critical section - only one test here
        shared_resource.modify()
```

### shared_queue()

Communicate between tests (inter-test data sharing):

```python
def test_producer(shared_queue):
    shared_queue.put("data")

def test_consumer(shared_queue):
    data = shared_queue.get()
```

### worker_temp_dir()

Provide isolated temporary directory per worker:

```python
def test_with_temp_file(worker_temp_dir):
    temp_file = worker_temp_dir / "test.txt"
    temp_file.write_text("data")
```

---

## ⚠️ Writing Parallel-Safe Tests

### DOs ✅

1. **Use fixtures instead of global state**
   ```python
   # ✅ GOOD - Thread-safe
   def test_with_fixture(isolated_test_data):
       data = isolated_test_data["key"]
       assert data == "value"
   ```

2. **Make tests independent**
   ```python
   # ✅ GOOD - Independent
   @pytest.mark.parallel_safe
   def test_api_a():
       result = call_api("A")
       assert result.status_code == 200
   
   @pytest.mark.parallel_safe
   def test_api_b():
       result = call_api("B")  # Different API
       assert result.status_code == 200
   ```

3. **Use worker-scoped resources**
   ```python
   # ✅ GOOD - Worker-isolated
   def test_worker_specific(worker_temp_dir):
       temp_file = worker_temp_dir / "unique.txt"
       temp_file.write_text("data")
   ```

### DON'Ts ❌

1. **Don't share global variables between tests**
   ```python
   # ❌ BAD - Not thread-safe
   GLOBAL_STATE = {}
   
   def test_a():
       GLOBAL_STATE["key"] = "value"
   
   def test_b():
       value = GLOBAL_STATE["key"]  # Race condition!
   ```

2. **Don't access shared resources without locks**
   ```python
   # ❌ BAD - Race condition
   DATABASE_CONNECTION = db.connect()
   
   def test_a():
       DATABASE_CONNECTION.query("SELECT * FROM users")
   
   def test_b():
       DATABASE_CONNECTION.query("SELECT * FROM users")  # Conflict!
   ```

3. **Don't modify shared files without coordination**
   ```python
   # ❌ BAD - File conflict
   def test_a():
       with open("shared.log", "w") as f:
           f.write("Test A\n")
   
   def test_b():
       with open("shared.log", "a") as f:  # Append conflict!
           f.write("Test B\n")
   ```

---

## 📊 Monitoring and Debugging

### See Worker Output

```bash
# pytest-xdist shows which worker is running which test
pytest -n 4 -v

# Output:
# gw0 [1] test_1 PASSED
# gw1 [1] test_2 PASSED
# gw2 [1] test_3 PASSED
# gw3 [1] test_4 PASSED
```

### Check Worker Isolation

```python
# Each worker has unique ID
def test_worker_id(worker_id):
    print(f"Running on worker: {worker_id}")
    # Outputs: gw0, gw1, gw2, etc.
```

### Session Identification

```python
# Each test run has a unique session ID
def test_session_id(session_id):
    print(f"Session ID: {session_id}")
    # Outputs: 8-character unique ID
```

---

## 🎯 Best Practices

1. **Mark tests as parallel-safe** when they don't depend on shared state
2. **Use resource locks** for critical sections
3. **Keep tests independent** - each test should work in isolation
4. **Use worker-scoped fixtures** for resources that need isolation
5. **Profile before scaling** - Don't blindly increase workers, measure speedup
6. **Handle resource contention** - Database connections, file handles, network ports
7. **Use load-scope** for better test distribution across workers

---

## 🚨 Common Issues and Solutions

### Issue: Tests Run Slower in Parallel

**Cause:** Contention on shared resources (database, filesystem, network)

**Solution:**
- Use connection pools
- Isolate database connections per worker
- Use unique temporary files per test

### Issue: Random Test Failures

**Cause:** Non-deterministic order causing dependencies

**Solution:**
- Use `pytest.mark.serial` for dependent tests
- Order tests to ensure dependencies run first
- Use `@pytest.mark.parallel_safe` for truly independent tests

### Issue: Worker Deadlocks

**Cause:** Tests waiting on each other incorrectly

**Solution:**
- Use proper lock ordering
- Implement timeouts for locks
- Avoid circular dependencies

---

## 📈 Performance Tips

1. **Start with small worker count** - Measure speedup
2. **Don't use more workers than CPU cores** - Diminishing returns
3. **Profile slow tests first** - Fix bottlenecks before scaling
4. **Use load-scope for better distribution** - Balance test load across workers
5. **Consider I/O vs CPU bound tests** - Different optimal worker counts

---

## 📝 Example Parallel Test Suite

```python
# tests/parallel/test_parallel_example.py
import pytest


@pytest.mark.parallel_safe
def test_parallel_api_a():
    """Independent API test - safe to run in parallel."""
    result = call_api("service-a")
    assert result.status_code == 200


@pytest.mark.parallel_safe
def test_parallel_api_b():
    """Another independent API test."""
    result = call_api("service-b")
    assert result.status_code == 200


@pytest.mark.serial
def test_sequential_operations():
    """Tests that must run in sequence - not parallel."""
    result_a = operation_a()
    result_b = operation_b()
    assert result_b.depends_on(result_a.id)
```

Run in parallel:
```bash
pytest tests/parallel/test_parallel_example.py -n 4
```

---

**Guide created:** 2026-02-11 17:25 UTC  
**Framework:** QA-FRAMEWORK  
**Status:** Parallel execution configured and documented
