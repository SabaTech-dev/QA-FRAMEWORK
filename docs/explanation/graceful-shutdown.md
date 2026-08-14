# Graceful Shutdown Module

## Overview

The graceful shutdown module provides comprehensive functionality for cleanly shutting down QA-FRAMEWORK services. It handles:
- Signal handling (SIGTERM, SIGINT)
- Connection tracking and draining
- Resource cleanup (Database, Redis, file handles, etc.)
- Configurable timeouts
- Progress monitoring
- Both FastAPI and standalone application support

## Features

### ✅ Core Features

1. **Signal Handling**: Automatically catches SIGTERM and SIGINT signals
2. **Connection Tracking**: Tracks all active connections and requests
3. **Connection Draining**: Waits for in-flight requests to complete
4. **Resource Cleanup**: Closes database, Redis, and custom resources
5. **Timeout Management**: Configurable timeouts with forced shutdown option
6. **Progress Logging**: Detailed logging of shutdown progress
7. **FastAPI Integration**: Middleware and event handlers for FastAPI apps
8. **Standalone Support**: Simple API for non-FastAPI applications

## Architecture

```
src/infrastructure/shutdown/
├── __init__.py                  # Module exports
├── models.py                    # Data models
├── connection_tracker.py        # Connection tracking
├── shutdown_manager.py          # Main shutdown orchestrator
├── fastapi_integration.py       # FastAPI-specific integration
└── standalone.py               # Standalone application helpers
```

## Quick Start

### FastAPI Application

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio as aioredis

from src.infrastructure.shutdown import (
    setup_fastapi_shutdown,
    shutdown_manager,
    register_database_connection,
    register_redis_connection,
)

app = FastAPI()

# Setup graceful shutdown (one line!)
setup_fastapi_shutdown(app)

@app.on_event("startup")
async def startup():
    # Initialize resources
    db_engine = create_async_engine("postgresql+asyncpg://...")
    redis_client = aioredis.Redis(host="localhost", port=6379)
    
    # Register for shutdown
    await register_database_connection(db_engine)
    await register_redis_connection(redis_client)

# That's it! Your app now has graceful shutdown
```

### Standalone Application

```python
import asyncio
from src.infrastructure.shutdown import StandaloneShutdown

async def main():
    # Create shutdown handler
    shutdown = StandaloneShutdown()
    shutdown.setup()  # Installs signal handlers
    
    # Register resources
    shutdown.register_database(db_engine)
    shutdown.register_redis(redis_client)
    
    # Main loop
    while not shutdown.is_shutting_down():
        await process_tasks()
    
    # Cleanup
    await shutdown.wait_and_cleanup()

asyncio.run(main())
```

## Components

### 1. ShutdownManager

The main orchestrator that manages the entire shutdown process.

```python
from src.infrastructure.shutdown import ShutdownManager, ResourceType

# Get global instance
manager = ShutdownManager()

# Or create with custom config
from src.infrastructure.shutdown import ShutdownConfig

config = ShutdownConfig(
    graceful_timeout=30.0,      # Total shutdown timeout
    drain_timeout=10.0,         # Connection drain timeout
    resource_close_timeout=5.0, # Per-resource close timeout
    force_after_timeout=True,   # Force close on timeout
)

manager = ShutdownManager(config)

# Register resources
manager.register_resource(
    name="database",
    resource_type=ResourceType.DATABASE,
    instance=db_engine,
    close_handler="dispose",  # Method to call for closing
    priority=100              # Lower = closed first
)

# Setup signal handlers
manager.setup_signal_handlers()

# Trigger shutdown
result = await manager.shutdown(reason="Manual shutdown")
```

### 2. ConnectionTracker

Tracks active connections and in-flight requests.

```python
from src.infrastructure.shutdown import ConnectionTracker, ResourceType

tracker = ConnectionTracker()

# Register a connection
conn_id = await tracker.register_connection(
    resource_type=ResourceType.HTTP_CLIENT,
    metadata={"path": "/api/test"}
)

# Track requests
await tracker.start_request(conn_id)
# ... process request ...
await tracker.end_request(conn_id)

# Check status
active = await tracker.get_active_connections_count()
in_flight = await tracker.get_in_flight_requests_count()

# Drain connections
result = await tracker.drain_connections(timeout=10.0)
```

### 3. FastAPI Integration

#### Middleware

Automatically rejects requests during shutdown and tracks in-flight requests.

```python
from fastapi import FastAPI
from src.infrastructure.shutdown import ShutdownMiddleware

app = FastAPI()
app.add_middleware(ShutdownMiddleware)
```

#### Setup Function

One-line setup for FastAPI apps.

```python
from src.infrastructure.shutdown import setup_fastapi_shutdown

app = FastAPI()
setup_fastapi_shutdown(app)  # Adds middleware and event handlers
```

#### Lifespan Pattern (FastAPI 0.93+)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.infrastructure.shutdown import create_shutdown_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    manager = ShutdownManager()
    manager.setup_signal_handlers()
    manager.register_resource("db", ResourceType.DATABASE, engine)
    
    yield
    
    # Shutdown happens automatically

app = FastAPI(lifespan=lifespan)
```

### 4. Standalone Helpers

#### StandaloneShutdown

Simple wrapper for non-FastAPI applications.

```python
from src.infrastructure.shutdown import StandaloneShutdown

shutdown = StandaloneShutdown()
shutdown.setup()
shutdown.register_database(engine)
shutdown.register_redis(redis_client)

while not shutdown.is_shutting_down():
    await do_work()

await shutdown.wait_and_cleanup()
```

#### Context Manager

```python
from src.infrastructure.shutdown import shutdown_context

with shutdown_context() as shutdown:
    shutdown.register_database(engine)
    
    while not shutdown.is_shutting_down():
        await process()
```

#### Background Task Manager

```python
from src.infrastructure.shutdown import BackgroundTaskManager

task_manager = BackgroundTaskManager()

await task_manager.start_task(
    "worker",
    lambda: worker_task(),
    restart_on_failure=True
)

await task_manager.stop_all(timeout=10.0)
```

## Configuration

### ShutdownConfig

```python
from src.infrastructure.shutdown import ShutdownConfig

config = ShutdownConfig(
    # Timeouts
    graceful_timeout=30.0,        # Total shutdown time
    drain_timeout=10.0,           # Time to drain connections
    resource_close_timeout=5.0,   # Time per resource
    
    # Behavior
    drain_check_interval=0.5,     # How often to check connections
    max_in_flight_requests=1000,  # Max requests to track
    force_after_timeout=True,     # Force shutdown on timeout
    log_progress=True,            # Log shutdown progress
    raise_on_error=False,         # Raise exceptions during shutdown
    
    # Hooks
    pre_shutdown_hooks=[],
    post_shutdown_hooks=[]
)
```

## Shutdown Process

The shutdown process follows these phases in order:

1. **INITIATED**: Shutdown begins
2. **STOPPING_NEW_REQUESTS**: Stop accepting new connections
3. **DRAINING_CONNECTIONS**: Wait for in-flight requests
4. **CLOSING_RESOURCES**: Close resources by priority
5. **FLUSHING_BUFFERS**: Flush any pending buffers
6. **COMPLETED**: Shutdown successful
7. **FORCED**: Forced shutdown (timeout)

### Shutdown Sequence

```python
# 1. Setup
manager.setup_signal_handlers()
manager.register_resource("redis", ResourceType.REDIS, redis, priority=90)
manager.register_resource("db", ResourceType.DATABASE, db, priority=100)

# 2. Normal operation
# ... app runs ...

# 3. Signal received (SIGTERM/SIGINT) or manual trigger
# Shutdown automatically starts

# 4. Shutdown phases execute:
# - Stop accepting new requests
# - Wait for active requests (up to drain_timeout)
# - Close Redis (priority 90)
# - Close Database (priority 100)
# - Log completion

# 5. Process exits cleanly
```

## Resource Types

```python
from src.infrastructure.shutdown import ResourceType

# Available types:
ResourceType.DATABASE      # Database connections
ResourceType.REDIS         # Redis connections
ResourceType.HTTP_CLIENT   # HTTP clients
ResourceType.FILE_HANDLE   # File handles
ResourceType.CUSTOM        # Custom resources
```

## Priority System

Resources are closed in priority order (lower number = closed first):

```python
# Close in this order:
shutdown_manager.register_resource("http_client", ..., priority=50)   # 1st
shutdown_manager.register_resource("redis", ..., priority=90)         # 2nd
shutdown_manager.register_resource("database", ..., priority=100)     # 3rd
```

## Monitoring

### Check Shutdown Status

```python
if shutdown_manager.is_shutting_down():
    print("Shutdown in progress")
```

### Get Progress

```python
progress = shutdown_manager.get_progress()

print(f"Phase: {progress.phase.value}")
print(f"Active connections: {progress.active_connections}")
print(f"Drained: {progress.drained_connections}")
print(f"Resources closed: {progress.closed_resources}/{progress.total_resources}")
print(f"Duration: {progress.duration_seconds}s")

if progress.errors:
    print(f"Errors: {progress.errors}")
```

### Get Statistics

```python
stats = shutdown_manager.get_stats()

print(f"Shutting down: {stats['is_shutting_down']}")
print(f"Phase: {stats['phase']}")
print(f"Resources: {stats['resources_count']}")
print(f"Connections: {stats['connection_stats']}")
```

## Best Practices

### 1. Register All Resources

Always register all resources that need cleanup:

```python
# ✅ Good
manager.register_resource("db", ResourceType.DATABASE, db_engine)
manager.register_resource("redis", ResourceType.REDIS, redis_client)
manager.register_resource("http_client", ResourceType.HTTP_CLIENT, httpx_client)

# ❌ Bad (resources not cleaned up)
# Just closing them manually in finally block
```

### 2. Set Appropriate Priorities

```python
# Close in correct order:
# - HTTP clients first (they might use DB/Redis)
# - Redis before DB (Redis might be used by DB)
# - Database last

manager.register_resource("http", ResourceType.HTTP_CLIENT, http, priority=50)
manager.register_resource("redis", ResourceType.REDIS, redis, priority=90)
manager.register_resource("db", ResourceType.DATABASE, db, priority=100)
```

### 3. Use Proper Close Methods

```python
# SQLAlchemy engine
manager.register_resource("db", ResourceType.DATABASE, engine, close_handler="dispose")

# Redis client
manager.register_resource("redis", ResourceType.REDIS, redis, close_handler="close")

# Custom resource
class MyResource:
    async def shutdown(self):
        # Custom cleanup
        pass

manager.register_resource("custom", ResourceType.CUSTOM, resource, close_handler="shutdown")
```

### 4. Add Shutdown Hooks for Custom Logic

```python
def flush_metrics():
    # Flush metrics before shutdown
    metrics_client.flush()

def notify_service_registry():
    # Deregister from service registry
    registry.deregister()

manager.add_pre_shutdown_hook(flush_metrics)
manager.add_pre_shutdown_hook(notify_service_registry)
```

### 5. Test Shutdown Behavior

```python
import pytest
from src.infrastructure.shutdown import ShutdownManager, ShutdownStatus

def test_graceful_shutdown():
    ShutdownManager.reset()
    manager = ShutdownManager()
    
    mock_db = Mock()
    mock_db.dispose = Mock()
    
    manager.register_resource("db", ResourceType.DATABASE, mock_db, close_handler="dispose")
    
    result = asyncio.run(manager.shutdown(reason="Test"))
    
    assert result.status == ShutdownStatus.SUCCESSFUL
    assert mock_db.dispose.called
    
    ShutdownManager.reset()
```

## Troubleshooting

### Shutdown Timeout

If shutdown times out:

```python
# Increase timeouts
config = ShutdownConfig(
    graceful_timeout=60.0,  # More time
    drain_timeout=30.0,
)

# Or force close on timeout
config = ShutdownConfig(
    graceful_timeout=30.0,
    force_after_timeout=True,  # Will force close resources
)
```

### Resources Not Closing

Ensure close method is specified:

```python
# Check what methods your resource has
print(dir(resource))  # Look for close, dispose, shutdown, etc.

# Specify the method explicitly
manager.register_resource(
    "my_resource",
    ResourceType.CUSTOM,
    resource,
    close_handler="cleanup"  # Use correct method name
)
```

### Connections Not Draining

Check connection tracking:

```python
# Verify connections are being tracked
stats = connection_tracker.get_stats()
print(f"Active: {stats['active_connections']}")
print(f"In-flight: {stats['total_in_flight_requests']}")

# Ensure you're calling start_request/end_request
await tracker.start_request(conn_id)
# ... process ...
await tracker.end_request(conn_id)
```

## Testing

Run the unit tests:

```bash
# Run all shutdown tests
pytest tests/unit/infrastructure/test_shutdown.py -v

# Run FastAPI integration tests
pytest tests/unit/infrastructure/test_fastapi_shutdown.py -v

# Run with coverage
pytest tests/unit/infrastructure/test_shutdown*.py --cov=src/infrastructure/shutdown
```

## Examples

See `examples/graceful_shutdown_examples.py` for comprehensive examples including:
- FastAPI applications
- Standalone applications
- Background task management
- Custom resources
- Testing patterns

## API Reference

### ShutdownManager

```python
class ShutdownManager:
    def register_resource(name, resource_type, instance, close_handler=None, priority=100)
    def unregister_resource(name) -> bool
    def setup_signal_handlers()
    def restore_signal_handlers()
    async def shutdown(reason="Manual shutdown", timeout=None) -> ShutdownResult
    def get_progress() -> ShutdownProgress
    def is_shutting_down() -> bool
    def add_pre_shutdown_hook(hook)
    def add_post_shutdown_hook(hook)
```

### ConnectionTracker

```python
class ConnectionTracker:
    async def register_connection(resource_type, connection_id=None, metadata=None) -> str
    async def deregister_connection(connection_id) -> bool
    async def start_request(connection_id) -> bool
    async def end_request(connection_id) -> bool
    async def drain_connections(timeout=None, check_interval=None) -> Dict[str, int]
    async def force_close_all() -> int
    def stop_accepting_new()
    def is_accepting_new() -> bool
    def get_stats() -> Dict[str, Any]
```

## Integration with QA-FRAMEWORK Dashboard

To integrate with the existing dashboard:

```python
# In dashboard/backend/main.py

from src.infrastructure.shutdown import (
    setup_fastapi_shutdown,
    shutdown_manager,
    ResourceType,
)
from database import engine
from core.cache import cache_manager

app = FastAPI(title="QA-Framework Dashboard API")

# Setup graceful shutdown
setup_fastapi_shutdown(app)

@app.on_event("startup")
async def startup_event():
    # Existing initialization
    await init_db()
    set_startup_complete()
    
    # Register resources for shutdown
    shutdown_manager.register_resource(
        "database_engine",
        ResourceType.DATABASE,
        engine,
        close_handler="dispose",
        priority=100
    )
    
    # Register Redis if using cache
    async_client = await cache_manager.get_async_client()
    shutdown_manager.register_resource(
        "redis_async",
        ResourceType.REDIS,
        async_client,
        close_handler="close",
        priority=90
    )
    
    logger.info("Dashboard initialized with graceful shutdown")
```

## Summary

The graceful shutdown module ensures QA-FRAMEWORK services can:
- ✅ Stop cleanly when receiving termination signals
- ✅ Complete in-flight requests before shutting down
- ✅ Close all resources properly (DB, Redis, etc.)
- ✅ Avoid data loss and corruption
- ✅ Work with both FastAPI and standalone applications
- ✅ Be easily tested and monitored

This completes TASK-011 from IMPROVEMENT_TASKS.md.
