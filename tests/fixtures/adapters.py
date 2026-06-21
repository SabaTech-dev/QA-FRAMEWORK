"""
Adapter fixtures for parallel test execution.

This module provides worker-isolated fixtures for HTTP clients and UI pages,
ensuring thread-safe parallel execution of API and UI tests.

Clean Architecture: Infrastructure/Adapter layer
SOLID Principles:
    - SRP: Each fixture manages one resource type
    - ISP: Minimal interface for each fixture
    - DIP: Depends on ConfigManager abstraction
"""

import asyncio
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import pytest
import httpx

# Playwright es una dependencia opcional (capa UI). Al guardar el import
# permitimos que la colección de tests funcione en entornos sin navegador
# (p. ej. CI ligero o el PoC de QA agéntico, que usa Playwright vía Node).
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page  # noqa: F401
except ImportError:  # pragma: no cover - depende del entorno
    async_playwright = None  # type: ignore[assignment]
    Browser = None  # type: ignore[assignment,misc]
    BrowserContext = None  # type: ignore[assignment,misc]
    Page = None  # type: ignore[assignment,misc]

from src.adapters.http.httpx_client import HTTPXClient
from src.adapters.ui.playwright_page import PlaywrightPage
from src.infrastructure.config.config_manager import QAConfig


# =============================================================================
# HTTP CLIENT FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def http_client(
    qa_config: QAConfig,
    worker_id: str,
) -> Generator[HTTPXClient, None, None]:
    """
    Provide an isolated HTTP client per test.

    This fixture creates a new HTTP client instance for each test,
    ensuring complete isolation between parallel tests.

    Args:
        qa_config: QA configuration fixture.
        worker_id: Current worker identifier.

    Yields:
        HTTPXClient instance configured for this test.

    Example:
        def test_api_call(http_client):
            response = http_client.get("https://api.example.com/users")
            assert response.status_code == 200

    Clean Architecture:
        Adapter layer - provides concrete HTTP client implementation.
    """
    # Create client with worker-specific configuration
    client = HTTPXClient(
        base_url=qa_config.api.base_url,
        timeout=qa_config.test.timeout,
    )

    # Add worker identification header for tracking
    client.headers.update(
        {
            "X-Test-Worker-ID": worker_id,
            "X-Test-Parallel": "true",
        }
    )

    try:
        yield client
    finally:
        # Ensure cleanup even if test fails
        client.close()


@pytest.fixture(scope="session")
def session_http_client(
    qa_config: QAConfig,
    worker_id: str,
) -> Generator[HTTPXClient, None, None]:
    """
    Provide a session-scoped HTTP client per worker.

    This fixture creates one HTTP client per worker for the entire session,
    improving performance while maintaining isolation.

    Args:
        qa_config: QA configuration fixture.
        worker_id: Current worker identifier.

    Yields:
        HTTPXClient instance shared across tests in the same worker.

    Example:
        def test_with_session_client(session_http_client):
            # Same client instance used across tests
            response = session_http_client.get("/api/users")

    Note:
        Use this for read-only operations to improve performance.
        For write operations, use the function-scoped http_client.
    """
    client = HTTPXClient(
        base_url=qa_config.api.base_url,
        timeout=qa_config.test.timeout,
    )

    client.headers.update(
        {
            "X-Test-Worker-ID": worker_id,
            "X-Test-Scope": "session",
        }
    )

    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="function")
async def async_http_client(
    qa_config: QAConfig,
    worker_id: str,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Provide an isolated async HTTP client per test.

    Args:
        qa_config: QA configuration fixture.
        worker_id: Current worker identifier.

    Yields:
        httpx.AsyncClient instance configured for this test.

    Example:
        async def test_async_api(async_http_client):
            response = await async_http_client.get("/api/users")
            assert response.status_code == 200
    """
    async with httpx.AsyncClient(
        base_url=qa_config.api.base_url,
        timeout=qa_config.test.timeout,
        headers={
            "X-Test-Worker-ID": worker_id,
            "X-Test-Parallel": "true",
        },
    ) as client:
        yield client


# =============================================================================
# UI BROWSER FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
async def browser(
    qa_config: QAConfig,
    worker_id: str,
) -> AsyncGenerator[Browser, None]:
    """
    Provide a browser instance per worker.

    This fixture creates one browser per worker for the entire session,
    with each test getting its own isolated browser context.

    Args:
        qa_config: QA configuration fixture.
        worker_id: Current worker identifier.

    Yields:
        Playwright Browser instance.

    Example:
        async def test_with_browser(browser):
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://example.com")

    Clean Architecture:
        Adapter layer - provides concrete browser implementation.
    """
    playwright = await async_playwright().start()

    browser_type = qa_config.ui.browser
    headless = qa_config.ui.headless

    if browser_type == "chromium":
        browser_instance = await playwright.chromium.launch(headless=headless)
    elif browser_type == "firefox":
        browser_instance = await playwright.firefox.launch(headless=headless)
    elif browser_type == "webkit":
        browser_instance = await playwright.webkit.launch(headless=headless)
    else:
        raise ValueError(f"Unsupported browser: {browser_type}")

    try:
        yield browser_instance
    finally:
        await browser_instance.close()
        await playwright.stop()


@pytest.fixture(scope="function")
async def browser_context(
    browser: Browser,
    qa_config: QAConfig,
    worker_id: str,
) -> AsyncGenerator[BrowserContext, None]:
    """
    Provide an isolated browser context per test.

    Each test gets its own browser context with isolated cookies,
    local storage, and session storage.

    Args:
        browser: Browser fixture instance.
        qa_config: QA configuration fixture.
        worker_id: Current worker identifier.

    Yields:
        Playwright BrowserContext instance.

    Example:
        async def test_with_context(browser_context):
            page = await browser_context.new_page()
            await page.goto("https://example.com")
    """
    # Create isolated context
    context = await browser.new_context(
        viewport={
            "width": qa_config.ui.viewport_width,
            "height": qa_config.ui.viewport_height,
        },
        record_video_dir="videos/" if qa_config.ui.video_on_failure else None,
    )

    # Add worker identification
    await context.add_init_script(f"""
        window.__TEST_WORKER_ID__ = "{worker_id}";
        window.__TEST_PARALLEL__ = true;
    """)

    try:
        yield context
    finally:
        await context.close()


@pytest.fixture(scope="function")
async def page(
    browser_context: BrowserContext,
    qa_config: QAConfig,
) -> AsyncGenerator[Page, None]:
    """
    Provide an isolated page per test.

    Each test gets its own page instance with automatic screenshot
    on failure if configured.

    Args:
        browser_context: Browser context fixture instance.
        qa_config: QA configuration fixture.

    Yields:
        Playwright Page instance.

    Example:
        async def test_page_navigation(page):
            await page.goto("https://example.com")
            assert await page.title() == "Example Domain"
    """
    page_instance = await browser_context.new_page()

    try:
        yield page_instance
    finally:
        # Take screenshot on failure if configured
        if qa_config.ui.screenshot_on_failure:
            try:
                # Screenshot logic would be implemented here
                pass
            except Exception:
                pass  # Don't fail if screenshot fails

        await page_instance.close()


@pytest.fixture(scope="function")
async def ui_page(
    page: Page,
    qa_config: QAConfig,
) -> AsyncGenerator[PlaywrightPage, None]:
    """
    Provide a wrapped UI page for high-level interactions.

    This fixture wraps the Playwright page with the PlaywrightPage
    adapter for consistent API across tests.

    Args:
        page: Playwright page fixture instance.
        qa_config: QA configuration fixture.

    Yields:
        PlaywrightPage adapter instance.

    Example:
        async def test_with_ui_page(ui_page):
            await ui_page.goto("https://example.com")
            await ui_page.click("button#submit")

    Clean Architecture:
        Adapter layer - wraps low-level Playwright with high-level API.
    """
    adapter = PlaywrightPage(page)

    try:
        yield adapter
    finally:
        # Cleanup handled by page fixture
        pass


# =============================================================================
# RESOURCE POOL FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def worker_resource_pool(worker_id: str) -> Dict[str, Any]:
    """
    Provide a resource pool for worker-scoped resources.

    Args:
        worker_id: Current worker identifier.

    Yields:
        Dictionary for storing worker-scoped resources.

    Example:
        def test_with_resource_pool(worker_resource_pool):
            worker_resource_pool["api_key"] = "secret"
            assert "api_key" in worker_resource_pool
    """
    pool: Dict[str, Any] = {}
    pool["worker_id"] = worker_id
    pool["created_at"] = __import__("time").time()

    yield pool

    # Cleanup
    pool.clear()


@pytest.fixture(scope="function")
def test_resource_tracker(
    worker_id: str,
    execution_context: Dict[str, Any],
) -> Generator[Dict[str, Any], None, None]:
    """
    Provide a resource tracker for monitoring test resources.

    Args:
        worker_id: Current worker identifier.
        execution_context: Execution context fixture.

    Yields:
        Dictionary tracking test resources.

    Example:
        def test_with_resource_tracker(test_resource_tracker):
            test_resource_tracker["api_calls"] = []
            # ... make API calls ...
            assert len(test_resource_tracker["api_calls"]) > 0
    """
    tracker: Dict[str, Any] = {
        "worker_id": worker_id,
        "resources": [],
        "timestamps": [],
    }

    yield tracker

    # Log resource usage for debugging parallel execution
    if tracker["resources"]:
        print(f"  [Worker {worker_id}] Resources used: {len(tracker['resources'])}")
