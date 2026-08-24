"""
Mobile Testing Configuration and Utilities.

Provides configuration management, device profiles, and utility functions
for mobile testing across different platforms.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml


class DeviceType(Enum):
    """Types of mobile devices."""

    EMULATOR = "emulator"
    SIMULATOR = "simulator"
    REAL_DEVICE = "real_device"
    CLOUD_DEVICE = "cloud_device"


@dataclass
class DeviceProfile:
    """Profile for a specific mobile device."""

    name: str
    platform: str  # android, ios
    platform_version: str
    device_type: DeviceType
    device_name: str
    screen_resolution: str | None = None
    screen_density: int | None = None
    appium_capabilities: dict[str, Any] = field(default_factory=dict)


@dataclass
class MobileTestConfig:
    """Configuration for mobile testing."""

    appium_server_url: str = "http://localhost:4723"
    implicit_wait: int = 10
    explicit_wait: int = 30
    screenshot_on_failure: bool = True
    screenshot_dir: str = "./screenshots"
    video_recording: bool = False
    video_dir: str = "./videos"
    device_profiles: dict[str, DeviceProfile] = field(default_factory=dict)
    default_profile: str | None = None


class MobileConfigManager:
    """
    Manages mobile testing configuration.

    Supports loading from YAML files and environment variables.
    """

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self._find_config_file()
        self._config: MobileTestConfig | None = None

    def _find_config_file(self) -> str | None:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config/mobile.yaml",
            "config/mobile.yml",
            "mobile.yaml",
            "mobile.yml",
            os.path.expanduser("~/.qa-framework/mobile.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def load_config(self) -> MobileTestConfig:
        """Load configuration from file."""
        if self._config:
            return self._config

        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)

            self._config = self._parse_config(data)
        else:
            self._config = MobileTestConfig()

        # Override with environment variables
        self._apply_env_overrides()

        return self._config

    def _parse_config(self, data: dict[str, Any]) -> MobileTestConfig:
        """Parse configuration dictionary."""
        config = MobileTestConfig(
            appium_server_url=data.get("appium_server_url", "http://localhost:4723"),
            implicit_wait=data.get("implicit_wait", 10),
            explicit_wait=data.get("explicit_wait", 30),
            screenshot_on_failure=data.get("screenshot_on_failure", True),
            screenshot_dir=data.get("screenshot_dir", "./screenshots"),
            video_recording=data.get("video_recording", False),
            video_dir=data.get("video_dir", "./videos"),
            default_profile=data.get("default_profile"),
        )

        # Parse device profiles
        profiles = data.get("device_profiles", {})
        for name, profile_data in profiles.items():
            config.device_profiles[name] = DeviceProfile(
                name=name,
                platform=profile_data["platform"],
                platform_version=profile_data["platform_version"],
                device_type=DeviceType(profile_data["device_type"]),
                device_name=profile_data["device_name"],
                screen_resolution=profile_data.get("screen_resolution"),
                screen_density=profile_data.get("screen_density"),
                appium_capabilities=profile_data.get("appium_capabilities", {}),
            )

        return config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if self._config:
            appium_url = os.getenv("APPIUM_SERVER_URL")
            if appium_url:
                self._config.appium_server_url = appium_url
            implicit_wait = os.getenv("MOBILE_IMPLICIT_WAIT")
            if implicit_wait:
                self._config.implicit_wait = int(implicit_wait)
            screenshot_on_failure = os.getenv("MOBILE_SCREENSHOT_ON_FAILURE")
            if screenshot_on_failure:
                self._config.screenshot_on_failure = screenshot_on_failure.lower() == "true"

    def get_device_profile(self, name: str | None = None) -> DeviceProfile | None:
        """Get device profile by name or default."""
        config = self.load_config()
        profile_name = name or config.default_profile

        if profile_name:
            return config.device_profiles.get(profile_name)

        return None

    def add_device_profile(self, profile: DeviceProfile) -> None:
        """Add a device profile."""
        if self._config:
            self._config.device_profiles[profile.name] = profile

    def save_config(self, path: str | None = None) -> None:
        """Save configuration to file."""
        if not self._config:
            return

        save_path = path or self.config_path or "config/mobile.yaml"

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        data: dict[str, Any] = {
            "appium_server_url": self._config.appium_server_url,
            "implicit_wait": self._config.implicit_wait,
            "explicit_wait": self._config.explicit_wait,
            "screenshot_on_failure": self._config.screenshot_on_failure,
            "screenshot_dir": self._config.screenshot_dir,
            "video_recording": self._config.video_recording,
            "video_dir": self._config.video_dir,
            "default_profile": self._config.default_profile,
            "device_profiles": {},
        }

        for name, profile in self._config.device_profiles.items():
            data["device_profiles"][name] = {
                "platform": profile.platform,
                "platform_version": profile.platform_version,
                "device_type": profile.device_type.value,
                "device_name": profile.device_name,
                "screen_resolution": profile.screen_resolution,
                "screen_density": profile.screen_density,
                "appium_capabilities": profile.appium_capabilities,
            }

        with open(save_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)


# Predefined device profiles
ANDROID_DEVICES = {
    "pixel_4": DeviceProfile(
        name="pixel_4",
        platform="android",
        platform_version="11.0",
        device_type=DeviceType.EMULATOR,
        device_name="Pixel 4",
        screen_resolution="1080x2280",
        screen_density=444,
    ),
    "pixel_5": DeviceProfile(
        name="pixel_5",
        platform="android",
        platform_version="12.0",
        device_type=DeviceType.EMULATOR,
        device_name="Pixel 5",
        screen_resolution="1080x2340",
        screen_density=432,
    ),
    "galaxy_s21": DeviceProfile(
        name="galaxy_s21",
        platform="android",
        platform_version="11.0",
        device_type=DeviceType.EMULATOR,
        device_name="Samsung Galaxy S21",
        screen_resolution="1080x2400",
        screen_density=421,
    ),
}

IOS_DEVICES = {
    "iphone_12": DeviceProfile(
        name="iphone_12",
        platform="ios",
        platform_version="14.5",
        device_type=DeviceType.SIMULATOR,
        device_name="iPhone 12",
        screen_resolution="1170x2532",
        screen_density=460,
    ),
    "iphone_13": DeviceProfile(
        name="iphone_13",
        platform="ios",
        platform_version="15.0",
        device_type=DeviceType.SIMULATOR,
        device_name="iPhone 13",
        screen_resolution="1170x2532",
        screen_density=460,
    ),
    "ipad_pro": DeviceProfile(
        name="ipad_pro",
        platform="ios",
        platform_version="15.0",
        device_type=DeviceType.SIMULATOR,
        device_name="iPad Pro (12.9-inch)",
        screen_resolution="2048x2732",
        screen_density=264,
    ),
}


def get_default_android_profile() -> DeviceProfile:
    """Get default Android device profile."""
    return ANDROID_DEVICES["pixel_4"]


def get_default_ios_profile() -> DeviceProfile:
    """Get default iOS device profile."""
    return IOS_DEVICES["iphone_12"]


def list_available_devices() -> dict[str, list[str]]:
    """List all available device profiles."""
    return {
        "android": list(ANDROID_DEVICES.keys()),
        "ios": list(IOS_DEVICES.keys()),
    }
