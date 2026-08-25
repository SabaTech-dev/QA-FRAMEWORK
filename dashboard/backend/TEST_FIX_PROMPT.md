# Fix 59 Redis Tests - Use Real Railway Redis (NO MOCKS)

## Context
You're working on QA-FRAMEWORK backend. We fixed Redis connection to use Railway, but 59 tests still fail because they expect mocked behavior.

## Current State
- **761 total tests**
- **698 passing (92%)** - These use real Redis correctly
- **59 failing (8%)** - These expect mocks

## Local Redis
```
REDIS_URL=redis://127.0.0.1:6379/0
```

Configured in:
- `tests/conftest.py` - Sets REDIS_URL from env
- `src/infrastructure/cache/test_cache.py` - Uses `os.getenv("REDIS_URL")`

## Your Task
Fix these 4 test files to use REAL Redis (no mocks):

### 1. tests/infrastructure/test_test_cache.py (18 failures)
**Remove all mocks:**
- Delete `mock_redis` fixture
- Remove `@patch` decorators
- Remove `Mock(spec=redis.Redis)`

**Update assertions for real Redis:**
- `test_get_keys_matching`: Redis KEYS returns list of strings (decode_responses=True in connection)
- `test_get_key_age_with_ttl`: TTL returns -2 for non-existent, -1 for no expiry, positive for seconds remaining
- `test_get_cache_size`: Use `DBSIZE` command (redis.dbsize())
- `test_get_memory_usage`: Use `INFO memory` command
- `test_clear_all`: Use `FLUSHDB` but ONLY on test keys (use prefix)
- `test_get_all_keys`: Use `KEYS *` carefully

**Add test isolation:**
```python
@pytest.fixture(autouse=True)
def cleanup_redis(self, test_cache):
    """Clean up test keys after each test"""
    yield
    # Delete all keys starting with test_
    keys = test_cache.redis.keys("test_*")
    if keys:
        test_cache.redis.delete(*keys)
```

**Keep InMemoryCache tests** - Those are unit tests, don't change them.

### 2. tests/services/test_batch_execution_service.py (19 failures)
**Problem:** Tests expect mocked cache behavior.

**Fix approach:**
- Service already uses real Redis (via CacheService -> TestCache)
- Remove any `@patch` for cache
- Update assertions:
  - Cache hits require actual cached data
  - TTL expiration is real (add small delays if needed)
  - Stats reflect actual operations

**Example fix:**
```python
def test_execute_batch_with_cache(self, batch_service, mock_executor):
    """Test batch execution with caching enabled"""
    test_ids = [1, 2, 3]

    # First run - cache miss
    results1 = batch_service.execute_batch(test_ids, mock_executor, use_cache=True)
    assert results1["stats"]["cache_misses"] == 3

    # Second run - cache hit
    results2 = batch_service.execute_batch(test_ids, mock_executor, use_cache=True)
    assert results2["stats"]["cache_hits"] == 3
```

### 3. tests/services/test_parallel_execution_service.py (19 failures)
**Same as batch_execution:**
- Remove cache mocks
- Use real Redis for SharedResourceManager locks
- Update LoadBalancer to work with real data

### 4. tests/unit/test_auth_service.py (3 failures)
**Investigate:** May not be Redis-related.
- Run these tests individually first
- Check error messages
- Fix token creation if needed

## Critical Rules

1. **NO MOCKS for Redis** - This is non-negotiable
2. **Use test key prefixes** - All keys should start with `test_` or `test_run_{uuid}_`
3. **Clean up after tests** - Delete test keys in teardown
4. **Don't break passing tests** - The 698 passing tests must stay passing
5. **Mark integration tests** - Add `@pytest.mark.integration` to Redis-dependent tests

## Success Criteria
```bash
# All tests must pass
python3 -m pytest --tb=short -q

# Coverage >= 80%
python3 -m pytest --cov=. --cov-report=term-missing | grep "TOTAL.*80%"
```

## How to Work

1. **Start with test_test_cache.py** - Fix the foundation
2. **Then batch_execution and parallel_execution** - They depend on cache
3. **Finally auth_service** - Separate issue
4. **Run tests frequently** - After each file fix
5. **Commit after each major fix** - Git commits with descriptive messages

## Commands
```bash
# Test single file
python3 -m pytest tests/infrastructure/test_test_cache.py -v

# Test with coverage
python3 -m pytest tests/infrastructure/test_test_cache.py --cov=src/infrastructure/cache --cov-report=term-missing

# Run all tests
python3 -m pytest --tb=short -q

# Check specific test
python3 -m pytest tests/infrastructure/test_test_cache.py::TestTestCache::test_get_cache_size -v
```

## Expected Time
30-45 minutes for all 59 tests.

BEGIN NOW. Fix tests/infrastructure/test_test_cache.py first.
