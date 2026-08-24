"""
Mobile Testing Adapter using Appium.

Provides mobile automation capabilities for Android and iOS testing:
- Cross-platform mobile testing
- Gesture support (tap, swipe, scroll, pinch)
- Device and emulator management
- Screenshot and video recording
- Element location strategies
- Mobile-specific assertions

Clean Architecture: Adapter layer
SOLID Principles:
    - SRP: Each class has single responsibility
    - OCP: Extensible through interfaces
    - DIP: Depends on abstractions
"""

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MobilePlatform(Enum):
    """Supported mobile platforms."""

    ANDROID = "android"
    IOS = "ios"


class GestureType(Enum):
    """Supported gesture types."""

    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SCROLL = "scroll"
    PINCH = "pinch"
    ZOOM = "zoom"


@dataclass
class MobileElement:
    """Represents a mobile UI element."""

    locator: str
    locator_type: str = "id"  # id, xpath, accessibility_id, class_name, etc.
    platform: MobilePlatform = MobilePlatform.ANDROID

    def __repr__(self) -> str:
        return f"MobileElement({self.locator_type}={self.locator})"


@dataclass
class Point:
    """Represents a 2D point on screen."""

    x: int
    y: int


@dataclass
class Size:
    """Represents screen or element size."""

    width: int
    height: int


@dataclass
class Rect:
    """Represents a rectangle (element bounds)."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Point:
        """Get center point of rectangle."""
        return Point(x=self.x + self.width // 2, y=self.y + self.height // 2)


@dataclass
class SwipeDirection:
    """Swipe direction vectors."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


@dataclass
class MobileCapabilities:
    """Mobile device capabilities configuration."""

    platform_name: MobilePlatform
    platform_version: str
    device_name: str
    app: str | None = None
    app_package: str | None = None
    app_activity: str | None = None
    automation_name: str | None = None
    auto_grant_permissions: bool = True
    no_reset: bool = False
    full_reset: bool = False
    new_command_timeout: int = 300
    additional_caps: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Appium capabilities dictionary."""
        caps = {
            "platformName": self.platform_name.value,
            "platformVersion": self.platform_version,
            "deviceName": self.device_name,
            "autoGrantPermissions": self.auto_grant_permissions,
            "noReset": self.no_reset,
            "fullReset": self.full_reset,
            "newCommandTimeout": self.new_command_timeout,
        }

        if self.app:
            caps["app"] = self.app
        if self.app_package:
            caps["appPackage"] = self.app_package
        if self.app_activity:
            caps["appActivity"] = self.app_activity
        if self.automation_name:
            caps["automationName"] = self.automation_name

        # Platform-specific defaults
        if self.platform_name == MobilePlatform.ANDROID and not self.automation_name:
            caps["automationName"] = "UiAutomator2"
        elif self.platform_name == MobilePlatform.IOS and not self.automation_name:
            caps["automationName"] = "XCUITest"

        if self.additional_caps:
            caps.update(self.additional_caps)

        return caps


class IMobileDriver(ABC):
    """
    Interface for mobile testing drivers.
    Implements Interface Segregation Principle.
    """

    @abstractmethod
    def find_element(self, locator: str, locator_type: str = "id") -> Any:
        """Find a mobile element."""

    @abstractmethod
    def find_elements(self, locator: str, locator_type: str = "id") -> list[Any]:
        """Find multiple mobile elements."""

    @abstractmethod
    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""

    @abstractmethod
    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 800
    ) -> None:
        """Swipe from start to end coordinates."""

    @abstractmethod
    def get_screenshot(self, filename: str | None = None) -> bytes | str:
        """Capture screenshot."""

    @abstractmethod
    def get_page_source(self) -> str:
        """Get current page XML source."""


class AppiumDriver(IMobileDriver):
    """
    Appium driver implementation for mobile testing.

    Features:
    - Android and iOS support
    - Gesture automation
    - Element interaction
    - Screenshot and recording
    - Context switching (native/web)
    """

    def __init__(
        self, capabilities: MobileCapabilities, appium_server_url: str = "http://localhost:4723"
    ):
        self.capabilities = capabilities
        self.server_url = appium_server_url
        self._driver: Any | None = None
        self._session_id: str | None = None

    def start(self) -> "AppiumDriver":
        """Start the Appium session."""
        try:
            from appium import webdriver

            self._driver = webdriver.Remote(
                command_executor=self.server_url, desired_capabilities=self.capabilities.to_dict()
            )
            self._session_id = self._driver.session_id
            return self
        except ImportError:
            raise RuntimeError(
                "Appium not installed. Install with: pip install Appium-Python-Client"
            )

    def stop(self) -> None:
        """Stop the Appium session."""
        if self._driver:
            self._driver.quit()
            self._driver = None
            self._session_id = None

    def __enter__(self) -> "AppiumDriver":
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

    @property
    def driver(self) -> Any:
        """Get underlying driver instance."""
        if not self._driver:
            raise RuntimeError("Driver not started. Call start() first.")
        return self._driver

    # Element Location

    def find_element(self, locator: str, locator_type: str = "id") -> Any:
        """Find a single element."""
        from appium.webdriver.common.appiumby import AppiumBy

        by_map = {
            "id": AppiumBy.ID,
            "xpath": AppiumBy.XPATH,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
            "class_name": AppiumBy.CLASS_NAME,
            "name": AppiumBy.NAME,
            "css_selector": AppiumBy.CSS_SELECTOR,
            "link_text": AppiumBy.LINK_TEXT,
            "partial_link_text": AppiumBy.PARTIAL_LINK_TEXT,
            "tag_name": AppiumBy.TAG_NAME,
            "android_uiautomator": AppiumBy.ANDROID_UIAUTOMATOR,
            "ios_predicate": AppiumBy.IOS_PREDICATE,
            "ios_class_chain": AppiumBy.IOS_CLASS_CHAIN,
        }

        by = by_map.get(locator_type.lower(), AppiumBy.ID)
        return self.driver.find_element(by, locator)

    def find_elements(self, locator: str, locator_type: str = "id") -> list[Any]:
        """Find multiple elements."""
        from appium.webdriver.common.appiumby import AppiumBy

        by_map = {
            "id": AppiumBy.ID,
            "xpath": AppiumBy.XPATH,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
            "class_name": AppiumBy.CLASS_NAME,
        }

        by = by_map.get(locator_type.lower(), AppiumBy.ID)
        return self.driver.find_elements(by, locator)

    def wait_for_element(self, locator: str, locator_type: str = "id", timeout: int = 10) -> Any:
        """Wait for element to be present."""
        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        by_map = {
            "id": AppiumBy.ID,
            "xpath": AppiumBy.XPATH,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
        }

        by = by_map.get(locator_type.lower(), AppiumBy.ID)
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, locator)))

    # Element Interaction

    def tap(self, x: int, y: int) -> None:
        """Tap at screen coordinates."""
        from appium.webdriver.common.touch_action import TouchAction

        action = TouchAction(self.driver)
        action.tap(x=x, y=y).perform()

    def tap_element(self, element: Any | MobileElement) -> None:
        """Tap on an element."""
        if isinstance(element, MobileElement):
            elem = self.find_element(element.locator, element.locator_type)
        else:
            elem = element
        elem.click()

    def double_tap(self, x: int, y: int) -> None:
        """Double tap at coordinates."""
        from appium.webdriver.common.touch_action import TouchAction

        action = TouchAction(self.driver)
        action.tap(x=x, y=y, count=2).perform()

    def long_press(self, x: int, y: int, duration: int = 1000) -> None:
        """Long press at coordinates."""
        from appium.webdriver.common.touch_action import TouchAction

        action = TouchAction(self.driver)
        action.long_press(x=x, y=y, duration=duration).release().perform()

    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 800
    ) -> None:
        """Swipe from start to end coordinates."""
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)

    def swipe_direction(self, direction: tuple[int, int], duration: int = 800) -> None:
        """Swipe in a direction using screen center."""
        size = self.get_screen_size()
        center_x = size.width // 2
        center_y = size.height // 2

        offset_x = size.width // 4 * direction[0]
        offset_y = size.height // 4 * direction[1]

        self.swipe(
            center_x - offset_x,
            center_y - offset_y,
            center_x + offset_x,
            center_y + offset_y,
            duration,
        )

    def scroll_to_element(
        self, locator: str, locator_type: str = "id", direction: str = "down"
    ) -> Any:
        """Scroll until element is found."""
        max_swipes = 10
        for _ in range(max_swipes):
            try:
                return self.find_element(locator, locator_type)
            except Exception:
                if direction == "down":
                    self.swipe_direction(SwipeDirection.DOWN)
                else:
                    self.swipe_direction(SwipeDirection.UP)

        raise RuntimeError(f"Element {locator} not found after scrolling")

    def pinch(self, x: int, y: int, scale: float = 0.5) -> None:
        """Pinch gesture (zoom out)."""
        # Use multi-touch action for pinch
        from appium.webdriver.common.multi_action import MultiAction
        from appium.webdriver.common.touch_action import TouchAction

        size = self.get_screen_size()
        offset = int(min(size.width, size.height) * scale)

        action1 = (
            TouchAction(self.driver).press(x=x - offset, y=y - offset).move_to(x=x, y=y).release()
        )
        action2 = (
            TouchAction(self.driver).press(x=x + offset, y=y + offset).move_to(x=x, y=y).release()
        )

        multi_action = MultiAction(self.driver)
        multi_action.add(action1, action2)
        multi_action.perform()

    def zoom(self, x: int, y: int, scale: float = 0.5) -> None:
        """Zoom gesture (zoom in)."""
        from appium.webdriver.common.multi_action import MultiAction
        from appium.webdriver.common.touch_action import TouchAction

        size = self.get_screen_size()
        offset = int(min(size.width, size.size.height) * scale)

        action1 = (
            TouchAction(self.driver).press(x=x, y=y).move_to(x=x - offset, y=y - offset).release()
        )
        action2 = (
            TouchAction(self.driver).press(x=x, y=y).move_to(x=x + offset, y=y + offset).release()
        )

        multi_action = MultiAction(self.driver)
        multi_action.add(action1, action2)
        multi_action.perform()

    # Text Input

    def type_text(
        self, locator: str, text: str, locator_type: str = "id", clear_first: bool = True
    ) -> None:
        """Type text into an element."""
        element = self.find_element(locator, locator_type)

        if clear_first:
            element.clear()

        element.send_keys(text)

    def hide_keyboard(self) -> None:
        """Hide the on-screen keyboard."""
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass  # Keyboard might not be present

    # Device Information

    def get_screen_size(self) -> Size:
        """Get screen dimensions."""
        size = self.driver.get_window_size()
        return Size(width=size["width"], height=size["height"])

    def get_device_info(self) -> dict[str, Any]:
        """Get device information."""
        return {
            "platform": self.capabilities.platform_name.value,
            "platform_version": self.capabilities.platform_version,
            "device_name": self.capabilities.device_name,
            "screen_size": self.get_screen_size(),
        }

    # Screenshots and Recording

    def get_screenshot(self, filename: str | None = None) -> bytes | str:
        """Capture screenshot."""
        screenshot = self.driver.get_screenshot_as_png()

        if filename:
            with open(filename, "wb") as f:
                f.write(screenshot)
            return filename

        return screenshot

    def start_screen_recording(self, **options: Any) -> None:
        """Start screen recording (Android only)."""
        if self.capabilities.platform_name == MobilePlatform.ANDROID:
            self.driver.start_recording_screen(**options)

    def stop_screen_recording(self, filename: str) -> str:
        """Stop screen recording and save to file."""
        if self.capabilities.platform_name == MobilePlatform.ANDROID:
            video_data = self.driver.stop_recording_screen()
            video_bytes = base64.b64decode(video_data)

            with open(filename, "wb") as f:
                f.write(video_bytes)

            return filename
        return ""

    def get_page_source(self) -> str:
        """Get current page XML source."""
        return self.driver.page_source

    # Context Management

    def get_contexts(self) -> list[str]:
        """Get available contexts (NATIVE_APP, WEBVIEW, etc.)."""
        return self.driver.contexts

    def switch_to_context(self, context: str) -> None:
        """Switch to a different context."""
        self.driver.switch_to.context(context)

    def switch_to_native(self) -> None:
        """Switch to native app context."""
        self.switch_to_context("NATIVE_APP")

    def switch_to_webview(self, index: int = 0) -> None:
        """Switch to webview context."""
        contexts = self.get_contexts()
        webviews = [c for c in contexts if "WEBVIEW" in c]
        if webviews and index < len(webviews):
            self.switch_to_context(webviews[index])

    # App Management

    def launch_app(self) -> None:
        """Launch the app."""
        self.driver.launch_app()

    def close_app(self) -> None:
        """Close the app."""
        self.driver.close_app()

    def reset_app(self) -> None:
        """Reset the app state."""
        self.driver.reset()

    def install_app(self, app_path: str) -> None:
        """Install an app."""
        self.driver.install_app(app_path)

    def remove_app(self, app_id: str) -> None:
        """Remove an app."""
        self.driver.remove_app(app_id)

    def is_app_installed(self, app_id: str) -> bool:
        """Check if app is installed."""
        return self.driver.is_app_installed(app_id)

    def activate_app(self, app_id: str) -> None:
        """Activate/foreground an app."""
        self.driver.activate_app(app_id)

    def terminate_app(self, app_id: str) -> None:
        """Terminate/background an app."""
        self.driver.terminate_app(app_id)

    def get_app_state(self, app_id: str) -> int:
        """Get app state (0=not installed, 1=not running, 2=background, 3=foreground, 4=running)."""
        return self.driver.query_app_state(app_id)

    # Device Actions

    def press_keycode(self, keycode: int) -> None:
        """Press a keycode (Android only)."""
        if self.capabilities.platform_name == MobilePlatform.ANDROID:
            self.driver.press_keycode(keycode)

    def shake_device(self) -> None:
        """Simulate device shake (iOS only)."""
        if self.capabilities.platform_name == MobilePlatform.IOS:
            self.driver.shake()

    def lock_device(self, seconds: int = 0) -> None:
        """Lock the device."""
        self.driver.lock(seconds)

    def unlock_device(self) -> None:
        """Unlock the device."""
        self.driver.unlock()

    def is_device_locked(self) -> bool:
        """Check if device is locked."""
        return self.driver.is_locked()


class MobileTestBuilder:
    """
    Builder pattern for constructing mobile tests.

    Example:
        test = (MobileTestBuilder()
            .with_android_capabilities("11", "Pixel 4")
            .with_app("/path/to/app.apk")
            .with_implicit_wait(10)
            .build())
    """

    def __init__(self):
        self._platform: MobilePlatform | None = None
        self._platform_version: str | None = None
        self._device_name: str | None = None
        self._app: str | None = None
        self._app_package: str | None = None
        self._app_activity: str | None = None
        self._additional_caps: dict[str, Any] = {}
        self._server_url: str = "http://localhost:4723"

    def with_android_capabilities(self, version: str, device: str) -> "MobileTestBuilder":
        """Set Android capabilities."""
        self._platform = MobilePlatform.ANDROID
        self._platform_version = version
        self._device_name = device
        return self

    def with_ios_capabilities(self, version: str, device: str) -> "MobileTestBuilder":
        """Set iOS capabilities."""
        self._platform = MobilePlatform.IOS
        self._platform_version = version
        self._device_name = device
        return self

    def with_app(self, app_path: str) -> "MobileTestBuilder":
        """Set app path."""
        self._app = app_path
        return self

    def with_app_package(self, package: str, activity: str) -> "MobileTestBuilder":
        """Set Android app package and activity."""
        self._app_package = package
        self._app_activity = activity
        return self

    def with_server_url(self, url: str) -> "MobileTestBuilder":
        """Set Appium server URL."""
        self._server_url = url
        return self

    def with_capability(self, key: str, value: Any) -> "MobileTestBuilder":
        """Add custom capability."""
        self._additional_caps[key] = value
        return self

    def build(self) -> AppiumDriver:
        """Build and return Appium driver."""
        if not self._platform:
            raise ValueError("Platform must be specified")

        caps = MobileCapabilities(
            platform_name=self._platform,
            platform_version=self._platform_version or "",
            device_name=self._device_name or "",
            app=self._app,
            app_package=self._app_package,
            app_activity=self._app_activity,
            additional_caps=self._additional_caps,
        )

        return AppiumDriver(caps, self._server_url)


class MobileElementActions:
    """
    Utility class for common mobile element actions.
    """

    def __init__(self, driver: AppiumDriver):
        self.driver = driver

    def tap(self, element: MobileElement) -> None:
        """Tap on element."""
        self.driver.tap_element(element)

    def type_text(self, element: MobileElement, text: str, clear_first: bool = True) -> None:
        """Type text into element."""
        self.driver.type_text(element.locator, text, element.locator_type, clear_first)

    def get_text(self, element: MobileElement) -> str:
        """Get element text."""
        elem = self.driver.find_element(element.locator, element.locator_type)
        return elem.text

    def is_displayed(self, element: MobileElement) -> bool:
        """Check if element is displayed."""
        try:
            elem = self.driver.find_element(element.locator, element.locator_type)
            return elem.is_displayed()
        except Exception:
            return False

    def is_enabled(self, element: MobileElement) -> bool:
        """Check if element is enabled."""
        try:
            elem = self.driver.find_element(element.locator, element.locator_type)
            return elem.is_enabled()
        except Exception:
            return False

    def get_location(self, element: MobileElement) -> Point:
        """Get element location."""
        elem = self.driver.find_element(element.locator, element.locator_type)
        loc = elem.location
        return Point(x=loc["x"], y=loc["y"])

    def get_size(self, element: MobileElement) -> Size:
        """Get element size."""
        elem = self.driver.find_element(element.locator, element.locator_type)
        size = elem.size
        return Size(width=size["width"], height=size["height"])


# Convenience functions


def create_android_driver(
    version: str,
    device: str,
    app_path: str | None = None,
    app_package: str | None = None,
    app_activity: str | None = None,
    server_url: str = "http://localhost:4723",
) -> AppiumDriver:
    """Factory function for creating Android driver."""
    builder = MobileTestBuilder()
    builder.with_android_capabilities(version, device)

    if app_path:
        builder.with_app(app_path)
    if app_package and app_activity:
        builder.with_app_package(app_package, app_activity)

    builder.with_server_url(server_url)
    return builder.build()


def create_ios_driver(
    version: str,
    device: str,
    app_path: str | None = None,
    server_url: str = "http://localhost:4723",
) -> AppiumDriver:
    """Factory function for creating iOS driver."""
    builder = MobileTestBuilder()
    builder.with_ios_capabilities(version, device)

    if app_path:
        builder.with_app(app_path)

    builder.with_server_url(server_url)
    return builder.build()
