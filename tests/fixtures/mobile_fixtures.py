"""
Mobile Testing Fixtures for Pytest.

Provides fixtures for mobile testing with Appium:
- Device profiles
- Appium driver instances
- Mobile elements
- Screenshot capture on failure
"""

import os
from pathlib import Path
from typing import Generator

import pytest

from src.adapters.mobile.appium_driver import AppiumDriver, create_android_driver, create_ios_driver
from src.adapters.mobile.mobile_config import (
    DeviceProfile,
    MobileConfigManager,
    get_default_android_profile,
    get_default_ios_profile,
)


@pytest.fixture(scope="session")
def mobile_config() -> MobileConfigManager:
    """Mobile testing configuration manager."""
    return MobileConfigManager()


@pytest.fixture(scope="session")
def appium_server_url() -> str:
    """Appium server URL from environment or default."""
    return os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")


@pytest.fixture(scope="session")
def android_device_profile() -> DeviceProfile:
    """Default Android device profile."""
    return get_default_android_profile()


@pytest.fixture(scope="session")
def ios_device_profile() -> DeviceProfile:
    """Default iOS device profile."""
    return get_default_ios_profile()


@pytest.fixture(scope="function")
def android_driver(
    appium_server_url: str,
    android_device_profile: DeviceProfile,
    request: pytest.FixtureRequest,
) -> Generator[AppiumDriver, None, None]:
    """
    Appium driver for Android testing.

    Automatically captures screenshot on test failure.
    """
    # Check if app path is provided via marker
    app_path_marker = request.node.get_closest_marker("android_app")
    app_path = app_path_marker.args[0] if app_path_marker else None

    driver = create_android_driver(
        version=android_device_profile.platform_version,
        device=android_device_profile.device_name,
        app_path=app_path,
        server_url=appium_server_url,
    )

    driver.start()

    yield driver

    # Capture screenshot on failure
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        screenshot_dir = Path("./screenshots")
        screenshot_dir.mkdir(exist_ok=True)
        screenshot_path = screenshot_dir / f"{request.node.name}_android.png"
        driver.get_screenshot(str(screenshot_path))

    driver.stop()


@pytest.fixture(scope="function")
def ios_driver(
    appium_server_url: str,
    ios_device_profile: DeviceProfile,
    request: pytest.FixtureRequest,
) -> Generator[AppiumDriver, None, None]:
    """
    Appium driver for iOS testing.

    Automatically captures screenshot on test failure.
    """
    # Check if app path is provided via marker
    app_path_marker = request.node.get_closest_marker("ios_app")
    app_path = app_path_marker.args[0] if app_path_marker else None

    driver = create_ios_driver(
        version=ios_device_profile.platform_version,
        device=ios_device_profile.device_name,
        app_path=app_path,
        server_url=appium_server_url,
    )

    driver.start()

    yield driver

    # Capture screenshot on failure
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        screenshot_dir = Path("./screenshots")
        screenshot_dir.mkdir(exist_ok=True)
        screenshot_path = screenshot_dir / f"{request.node.name}_ios.png"
        driver.get_screenshot(str(screenshot_path))

    driver.stop()


@pytest.fixture(scope="function")
def mobile_screenshot_dir() -> Path:
    """Directory for mobile screenshots."""
    screenshot_dir = Path("./screenshots/mobile")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir


@pytest.fixture(scope="function")
def mobile_video_dir() -> Path:
    """Directory for mobile recordings."""
    video_dir = Path("./videos/mobile")
    video_dir.mkdir(parents=True, exist_ok=True)
    return video_dir


# Custom markers
def pytest_configure(config: pytest.Config) -> None:
    """Configure mobile testing markers."""
    config.addinivalue_line("markers", "android: mark test as Android mobile test")
    config.addinivalue_line("markers", "ios: mark test as iOS mobile test")
    config.addinivalue_line("markers", "mobile: mark test as mobile test")
    config.addinivalue_line("markers", "android_app(path): specify Android app path")
    config.addinivalue_line("markers", "ios_app(path): specify iOS app path")
    config.addinivalue_line("markers", "device_profile(name): specify device profile")
    config.addinivalue_line("markers", "screenshot_on_failure: capture screenshot on test failure")
    config.addinivalue_line("markers", "video_recording: record video during test")
