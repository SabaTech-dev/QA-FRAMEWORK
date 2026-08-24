"""
Advanced Test Fixtures for QA Framework.

This package provides sophisticated testing utilities organized by architectural layers:
- factories: Test data factories (UserFactory, ProductFactory, OrderFactory, etc.)
- patterns: Test patterns (AAA, BDD, Table-driven, Retry, etc.)
- advanced_fixtures: Pytest fixtures organized by layers
- adapters: Adapter-specific fixtures (HTTP, UI, etc.)

Usage:
    from tests.fixtures import UserFactory, ObjectMother
    from tests.fixtures import using_aaa, using_bdd
    from tests.fixtures import AAAPattern, GivenWhenThen
"""

# Fixture exports (for type hints)
from tests.fixtures.advanced_fixtures import (
    aaa_pattern,
    api_request_factory,
    bdd_scenario,
    execution_context,
    faker_instance,
    isolated_event_loop,
    isolated_test_data,
    mock_api_client,
    mock_async_http_client,
    mock_cache,
    mock_database,
    mock_http_client,
    mock_message_broker,
    mock_ui_driver,
    object_mother,
    order_factory,
    product_factory,
    resource_lock,
    retry_handler,
    scenario_builder,
    session_id,
    shared_message_queue,
    temp_directory,
    test_config,
    test_data_container,
    test_data_table,
    test_isolation,
    test_run_timestamp,
    thread_pool,
    timer,
    unique_test_id,
    user_factory,
    worker_temp_dir,
)

# Core factory classes
from tests.fixtures.factories import (
    APIRequestData,
    APIRequestFactory,
    DataBuilder,
    ObjectMother,
    OrderData,
    OrderFactory,
    ProductData,
    ProductFactory,
    Sequence,
    TestScenarioBuilder,
    UserData,
    UserFactory,
    create_data_builder,
    create_object_mother,
    create_order_factory,
    create_product_factory,
    create_user_factory,
)

# Pattern classes
from tests.fixtures.patterns import (
    AAAPattern,
    GivenWhenThen,
    ParameterizedTestBuilder,
    RetryPattern,
    TableDrivenTests,
    TestDataTable,
    TestDoubleFactory,
    TestIsolationManager,
    TestScenario,
    TestStep,
    TestSuiteBuilder,
    create_isolation_manager,
    create_test_table,
    using_aaa,
    using_bdd,
    with_retry,
)

__all__ = [
    # Factories
    "UserFactory",
    "ProductFactory",
    "OrderFactory",
    "APIRequestFactory",
    "ObjectMother",
    "TestScenarioBuilder",
    "DataBuilder",
    "Sequence",
    "UserData",
    "ProductData",
    "OrderData",
    "APIRequestData",
    # Factory functions
    "create_user_factory",
    "create_product_factory",
    "create_order_factory",
    "create_object_mother",
    "create_data_builder",
    # Patterns
    "AAAPattern",
    "GivenWhenThen",
    "TableDrivenTests",
    "TestDataTable",
    "TestScenario",
    "TestStep",
    "TestIsolationManager",
    "RetryPattern",
    "TestDoubleFactory",
    "TestSuiteBuilder",
    "ParameterizedTestBuilder",
    # Pattern functions
    "using_aaa",
    "using_bdd",
    "create_test_table",
    "create_isolation_manager",
    "with_retry",
    # Fixture types (for type hints)
    "user_factory",
    "product_factory",
    "order_factory",
    "api_request_factory",
    "object_mother",
    "scenario_builder",
    "faker_instance",
    "aaa_pattern",
    "bdd_scenario",
    "test_isolation",
    "retry_handler",
    "test_data_table",
    "timer",
    "session_id",
    "test_run_timestamp",
    "test_config",
    "thread_pool",
    "shared_message_queue",
    "resource_lock",
    "temp_directory",
    "worker_temp_dir",
    "mock_database",
    "mock_cache",
    "mock_message_broker",
    "mock_http_client",
    "mock_async_http_client",
    "mock_ui_driver",
    "mock_api_client",
    "isolated_event_loop",
    "unique_test_id",
    "isolated_test_data",
    "test_data_container",
    "execution_context",
]
