"""UI Page Interface and Implementation with Playwright"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class IUIPage(ABC):
    """
    Interface for UI page objects (Single Responsibility Principle).

    This interface defines the contract for all UI page adapters,
    following the Interface Segregation Principle (ISP) from SOLID.
    """

    @abstractmethod
    async def goto(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
        """
        pass

    @abstractmethod
    async def click(self, selector: str) -> None:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
        """
        pass

    @abstractmethod
    async def fill(self, selector: str, value: str) -> None:
        """
        Fill an input field with a value.

        Args:
            selector: CSS selector for the input
            value: Value to fill
        """
        pass

    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds (default: 30000)
        """
        pass

    @abstractmethod
    async def get_text(self, selector: str) -> str:
        """
        Get text content of an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """
        pass

    @abstractmethod
    async def is_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector for the element

        Returns:
            True if visible, False otherwise
        """
        pass

    @abstractmethod
    async def screenshot(self, path: str) -> None:
        """
        Take a screenshot of the current page.

        Args:
            path: Path to save the screenshot
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the browser/page."""
        pass


class PlaywrightPage(IUIPage):
    """
    Playwright implementation of UI page interface.

    This adapter implements the IUIPage interface, following
    the Dependency Inversion Principle (DIP) from SOLID.

    Attributes:
        browser_type: Type of browser (chromium, firefox, webkit)
        headless: Whether to run in headless mode
        viewport: Viewport dimensions (width, height)
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        viewport: Optional[tuple] = None,
    ):
        """
        Initialize Playwright page.

        Args:
            browser_type: Type of browser (chromium, firefox, webkit)
            headless: Whether to run in headless mode (default: True)
            viewport: Viewport dimensions as tuple (width, height)
        """
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.viewport = viewport or (1920, 1080)

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _init_browser(self) -> None:
        """Initialize browser if not already initialized."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

            # Get browser type
            if self.browser_type == "chromium":
                browser_launcher = self._playwright.chromium
            elif self.browser_type == "firefox":
                browser_launcher = self._playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self._playwright.webkit
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            # Launch browser
            self._browser = await browser_launcher.launch(headless=self.headless)

            # Create context with viewport
            self._context = await self._browser.new_context(
                viewport={"width": self.viewport[0], "height": self.viewport[1]}
            )

            # Create page
            self._page = await self._context.new_page()

    async def goto(self, url: str) -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
        """
        await self._init_browser()
        await self._page.goto(url, wait_until="networkidle")

    async def click(self, selector: str) -> None:
        """
        Click on an element.

        Args:
            selector: CSS selector for the element
        """
        await self._init_browser()
        await self._page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        """
        Fill an input field with a value.

        Args:
            selector: CSS selector for the input
            value: Value to fill
        """
        await self._init_browser()
        await self._page.fill(selector, value)

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> None:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds (default: 30000)
        """
        await self._init_browser()
        await self._page.wait_for_selector(selector, timeout=timeout)

    async def get_text(self, selector: str) -> str:
        """
        Get text content of an element.

        Args:
            selector: CSS selector for the element

        Returns:
            Text content of the element
        """
        await self._init_browser()
        element = await self._page.query_selector(selector)
        return await element.text_content() if element else ""

    async def is_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector for the element

        Returns:
            True if visible, False otherwise
        """
        await self._init_browser()
        element = await self._page.query_selector(selector)
        return await element.is_visible() if element else False

    async def screenshot(self, path: str) -> None:
        """
        Take a screenshot of the current page.

        Args:
            path: Path to save the screenshot
        """
        await self._init_browser()
        await self._page.screenshot(path=path)

    async def close(self) -> None:
        """Close the browser and cleanup resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None

    async def __aenter__(self) -> "PlaywrightPage":
        """Async context manager entry."""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
