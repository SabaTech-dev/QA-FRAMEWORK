# Performance Testing Module

The Performance Testing Module provides comprehensive load testing, benchmarking, and stress testing capabilities for APIs and web applications.

## Overview

This module supports multiple load testing tools:
- **Locust**: Python-based scalable load testing
- **k6**: Modern Go-based load testing
- **Apache Bench (ab)**: Simple command-line benchmarking

## Architecture

The module follows Clean Architecture principles with the following components:

```
src/adapters/performance/
├── __init__.py              # Module exports
├── performance_client.py    # Main facade client
├── metrics_collector.py     # Metrics collection
├── load_test_runner.py      # Load test adapters
└── benchmark_runner.py      # Benchmark testing
```

## Quick Start

### Load Testing

```python
from src.adapters.performance import PerformanceClient

async def run_load_test():
    client = PerformanceClient(tool="auto")
    
    results = await client.load_test(
        target_url="http://api.example.com/endpoint",
        users=100,           # Concurrent users
        duration=60,         # Test duration in seconds
        ramp_up=10           # Ramp-up time
    )
    
    print(f"Success: {results['success']}")
    print(f"Results: {results['results']}")
    
    await client.close()
```

### Benchmark Testing

```python
from src.adapters.performance import PerformanceClient
from src.adapters.http import HTTPXClient

async def run_benchmark():
    http_client = HTTPXClient(base_url="http://api.example.com")
    client = PerformanceClient(http_client=http_client)
    
    result = await client.benchmark(
        target_url="/endpoint",
        requests=1000
    )
    
    print(f"Average response time: {result.avg_time}ms")
    print(f"Throughput: {result.throughput} req/s")
    
    await client.close()
```

### Stress Testing

```python
async def run_stress_test():
    client = PerformanceClient(tool="auto")
    
    results = await client.stress_test(
        target_url="http://api.example.com/endpoint",
        start_users=10,
        max_users=200,
        step_users=10,
        step_duration=30
    )
    
    print(f"Max users reached: {results['max_users_reached']}")
    print(f"Breaking point: {results.get('break_point', 'None')}")
```

## Components

### PerformanceClient

The main facade class that provides unified access to all performance testing features.

**Key Methods:**
- `load_test()` - Run load tests
- `benchmark()` - Run benchmark tests
- `stress_test()` - Run stress tests
- `run_comparison()` - Compare different configurations

### MetricsCollector

Collects and analyzes performance metrics during tests.

```python
from src.adapters.performance import MetricsCollector

collector = MetricsCollector()
collector.start_collection()

# During test execution
collector.record_response_time(150.5)
collector.record_error("timeout", "Connection timeout")

collector.stop_collection()
metrics = collector.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Error rate: {metrics['error_rate']}%")
print(f"Avg response time: {metrics['response_times']['avg']}ms")
print(f"P95: {metrics['response_times']['p95']}ms")
print(f"P99: {metrics['response_times']['p99']}ms")
```

### LoadTestRunner Adapters

#### LocustAdapter

```python
from src.adapters.performance import LocustAdapter

adapter = LocustAdapter(locustfile="locustfile.py")
results = await adapter.run_load_test(
    target_url="http://api.example.com",
    users=100,
    duration=60
)
```

#### K6Adapter

```python
from src.adapters.performance import K6Adapter

adapter = K6Adapter(script="test.js")
results = await adapter.run_load_test(
    target_url="http://api.example.com",
    users=100,
    duration=60
)
```

#### ApacheBenchAdapter

```python
from src.adapters.performance import ApacheBenchAdapter

adapter = ApacheBenchAdapter()
results = await adapter.run_load_test(
    target_url="http://api.example.com",
    users=10,
    duration=30
)
```

### BenchmarkRunner

```python
from src.adapters.performance import BenchmarkRunner

runner = BenchmarkRunner()

# Benchmark async function
async def my_async_func():
    # Your async code
    pass

result = await runner.benchmark_async(
    func=my_async_func,
    iterations=1000,
    warmup_iterations=10
)

# Benchmark sync function
def my_sync_func():
    # Your sync code
    pass

result = runner.benchmark_sync(
    func=my_sync_func,
    iterations=1000
)

# Compare multiple benchmarks
results = [
    result1,
    result2,
    result3
]
comparison = runner.compare_benchmarks(results)
```

## Configuration

Add to your `config/qa.yaml`:

```yaml
performance:
  tool: auto                    # auto, locust, k6, ab
  default_users: 10
  default_duration: 60
  default_ramp_up: 5
  
  metrics:
    collect_response_times: true
    collect_throughput: true
    collect_error_rates: true
  
  thresholds:
    max_avg_response_time_ms: 500
    max_error_rate_percent: 5
    min_throughput_rps: 10
```

## Best Practices

1. **Start Small**: Begin with low user counts and short durations
2. **Use Warmup**: Always include warmup iterations to stabilize results
3. **Monitor Resources**: Watch server resources during tests
4. **Test Gradually**: Increase load gradually to find breaking points
5. **Compare Results**: Run comparison tests with different configurations
6. **Set Thresholds**: Define performance thresholds and fail tests when exceeded

## Requirements

- **Locust**: `pip install locust`
- **k6**: Install from https://k6.io/docs/getting-started/installation/
- **Apache Bench**: `apt-get install apache2-utils` (Ubuntu/Debian)

## Troubleshooting

### Tool Not Found

If you get "Tool not installed" errors:

1. Check tool availability:
```python
from src.adapters.performance import K6Adapter
adapter = K6Adapter()
available = await adapter.is_available()
print(f"k6 available: {available}")
```

2. Install missing tools or use `tool="auto"` to auto-detect

### High Memory Usage

For long-duration tests:
- Use streaming metrics collection
- Reduce metrics sampling frequency
- Use file-based result storage

### Inaccurate Results

If results seem inconsistent:
- Increase warmup iterations
- Run tests multiple times
- Check network conditions
- Verify server capacity

## Examples

See `examples/performance_testing_example.py` for complete working examples.