"""
Mobile Testing Examples.

Demonstrates usage of the mobile testing adapter with Appium.
"""

import pytest

from src.adapters.mobile.appium_driver import (
    AppiumDriver,
    MobileElement,
    MobilePlatform,
    SwipeDirection,
)


@pytest.mark.mobile
@pytest.mark.android
class TestAndroidApp:
    """Example tests for Android applications."""

    def test_app_launch(self, android_driver: AppiumDriver) -> None:
        """Test that the app launches successfully."""
        # Verify driver is initialized
        assert android_driver.driver is not None
        assert android_driver._session_id is not None

        # Get device info
        device_info = android_driver.get_device_info()
        assert device_info["platform"] == "android"
        assert "device_name" in device_info

    def test_element_interaction(self, android_driver: AppiumDriver) -> None:
        """Test basic element interaction."""
        # Define element
        login_button = MobileElement(
            locator="com.example.app:id/login_button",
            locator_type="id",
            platform=MobilePlatform.ANDROID,
        )

        # Check if element exists
        if android_driver.is_displayed(login_button):
            # Tap element
            android_driver.tap_element(login_button)

    def test_text_input(self, android_driver: AppiumDriver) -> None:
        """Test text input functionality."""
        # Type text into field
        android_driver.type_text(
            locator="com.example.app:id/username_field",
            text="testuser",
            locator_type="id",
            clear_first=True,
        )

        # Hide keyboard
        android_driver.hide_keyboard()

    def test_swipe_gesture(self, android_driver: AppiumDriver) -> None:
        """Test swipe gesture."""
        # Swipe up
        android_driver.swipe_direction(SwipeDirection.UP)

        # Swipe down
        android_driver.swipe_direction(SwipeDirection.DOWN)

        # Custom swipe
        size = android_driver.get_screen_size()
        android_driver.swipe(
            start_x=size.width // 2,
            start_y=size.height * 3 // 4,
            end_x=size.width // 2,
            end_y=size.height // 4,
            duration=500,
        )

    def test_screenshot_capture(self, android_driver: AppiumDriver, mobile_screenshot_dir) -> None:
        """Test screenshot capture."""
        # Take screenshot
        screenshot_path = mobile_screenshot_dir / "test_screenshot.png"
        _result = android_driver.get_screenshot(str(screenshot_path))

        # Verify screenshot was saved
        assert screenshot_path.exists()

    def test_app_state_management(self, android_driver: AppiumDriver) -> None:
        """Test app state transitions."""
        app_package = "com.example.app"

        # Check if app is installed
        is_installed = android_driver.is_app_installed(app_package)

        if is_installed:
            # Launch app
            android_driver.launch_app()

            # Get app state
            state = android_driver.get_app_state(app_package)
            assert state in [3, 4]  # foreground or running

            # Background app
            android_driver.terminate_app(app_package)

            # Foreground app again
            android_driver.activate_app(app_package)


@pytest.mark.mobile
@pytest.mark.ios
class TestiOSApp:
    """Example tests for iOS applications."""

    def test_app_launch(self, ios_driver: AppiumDriver) -> None:
        """Test that the iOS app launches successfully."""
        assert ios_driver.driver is not None

        device_info = ios_driver.get_device_info()
        assert device_info["platform"] == "ios"

    def test_element_locator_strategies(self, ios_driver: AppiumDriver) -> None:
        """Test different element locator strategies."""
        # By accessibility ID (preferred for iOS)
        element = ios_driver.find_element(locator="Login Button", locator_type="accessibility_id")
        assert element is not None

        # By iOS predicate
        element = ios_driver.find_element(
            locator="type == 'XCUIElementTypeButton' AND label == 'Submit'",
            locator_type="ios_predicate",
        )

        # By iOS class chain
        elements = ios_driver.find_elements(
            locator="**/XCUIElementTypeButton[`label == 'Option'`]", locator_type="ios_class_chain"
        )
        assert len(elements) >= 0

    def test_ios_specific_gestures(self, ios_driver: AppiumDriver) -> None:
        """Test iOS-specific gestures."""
        # Shake device (iOS only)
        ios_driver.shake_device()

    def test_context_switching(self, ios_driver: AppiumDriver) -> None:
        """Test switching between native and webview contexts."""
        # Get available contexts
        contexts = ios_driver.get_contexts()

        if len(contexts) > 1:
            # Switch to webview
            ios_driver.switch_to_webview()

            # Do web operations...

            # Switch back to native
            ios_driver.switch_to_native()


class TestCrossPlatform:
    """Cross-platform mobile tests."""

    def test_common_functionality(self) -> None:
        """
        Test that works on both platforms.
        Use platform checks for platform-specific behavior.
        """
        # This would use a parameterized driver fixture

    @pytest.mark.parametrize("platform", ["android", "ios"])
    def test_platform_specific(self, platform: str) -> None:
        """Parametrized test for multiple platforms."""
        # Platform-specific test logic


# Markers usage examples
@pytest.mark.android_app("/path/to/app.apk")
@pytest.mark.screenshot_on_failure
@pytest.mark.video_recording
class TestWithAdvancedFeatures:
    """Tests using advanced fixture features."""

    def test_with_custom_app(self, android_driver: AppiumDriver) -> None:
        """Test using custom app specified via marker."""
        # The android_driver fixture will use the app path from marker


# Practical usage example
class TestLoginFlow:
    """Real-world example: Testing a login flow."""

    @pytest.mark.android
    def test_successful_login(self, android_driver: AppiumDriver) -> None:
        """Test successful login flow."""
        # Define elements
        username_field = MobileElement(locator="com.example.app:id/username", locator_type="id")
        password_field = MobileElement(locator="com.example.app:id/password", locator_type="id")
        login_button = MobileElement(locator="com.example.app:id/login_button", locator_type="id")

        # Enter credentials
        android_driver.type_text(username_field.locator, "testuser", username_field.locator_type)

        android_driver.type_text(password_field.locator, "password123", password_field.locator_type)

        # Tap login button
        android_driver.tap_element(login_button)

        # Verify login success (check for dashboard element)
        dashboard = MobileElement(locator="com.example.app:id/dashboard", locator_type="id")

        # Wait for element with explicit wait
        element = android_driver.wait_for_element(
            dashboard.locator, dashboard.locator_type, timeout=10
        )

        assert element is not None
        assert element.is_displayed()
