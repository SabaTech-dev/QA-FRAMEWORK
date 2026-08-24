"""Configuration management with support for YAML, JSON, ENV"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class TestConfig(BaseModel):
    """Test execution configuration"""

    model_config = ConfigDict(extra="allow")

    environment: str = "development"
    parallel_workers: int = 4
    timeout: int = 30
    retry_failed: int = 0


class APIConfig(BaseModel):
    """API configuration"""

    model_config = ConfigDict(extra="allow")

    base_url: str = "http://localhost:8000"
    auth_type: str = "none"
    token: str | None = None
    username: str | None = None
    password: str | None = None


class UIConfig(BaseModel):
    """UI testing configuration"""

    model_config = ConfigDict(extra="allow")

    browser: str = "chromium"
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    screenshot_on_failure: bool = True
    video_on_failure: bool = False


class AllureConfig(BaseModel):
    """Allure reporting configuration"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    results_dir: str = "allure-results"
    report_dir: str = "reports/allure-report"
    screenshots_on_failure: bool = True
    clean_results: bool = True


class HTMLReportConfig(BaseModel):
    """HTML reporting configuration"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    report_dir: str = "reports/html-report"


class JSONReportConfig(BaseModel):
    """JSON reporting configuration"""

    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    report_dir: str = "reports/json-report"


class ReportingConfig(BaseModel):
    """Reporting configuration"""

    model_config = ConfigDict(extra="allow")

    allure: AllureConfig = Field(default_factory=AllureConfig)
    html: HTMLReportConfig = Field(default_factory=HTMLReportConfig)
    json: JSONReportConfig = Field(default_factory=JSONReportConfig)
    screenshots: str = "on_failure"  # on_failure, always, never


class QAConfig(BaseSettings):
    """Main QA Framework configuration"""

    model_config = ConfigDict(
        extra="allow", env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    test: TestConfig = Field(default_factory=TestConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


class ConfigManager:
    """
    Configuration manager supporting YAML, JSON, and ENV.

    This class follows Single Responsibility Principle (SRP) by only
    handling configuration loading and management.
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path or Path("config/qa.yaml")
        self._config: QAConfig | None = None

    def load_config(self) -> QAConfig:
        """
        Load configuration from file and environment.

        Returns:
            QAConfig object with loaded configuration
        """
        if self.config_path.exists():
            config_data = self._load_file(self.config_path)
            return QAConfig(**config_data)
        else:
            # Use default configuration
            return QAConfig()

    def _load_file(self, file_path: Path) -> dict[str, Any]:
        """
        Load configuration from file.

        Args:
            file_path: Path to configuration file

        Returns:
            Dictionary with configuration data
        """
        from typing import cast

        with open(file_path, "r") as f:
            if file_path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f) or {}
                return cast(dict[str, Any], data)
            elif file_path.suffix == ".json":
                import json

                data = json.load(f)
                return cast(dict[str, Any], data)
            else:
                raise ValueError(f"Unsupported config file format: {file_path.suffix}")

    def get_config(self) -> QAConfig:
        """Get loaded configuration (load if not loaded)"""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def reload(self) -> QAConfig:
        """Reload configuration from file"""
        self._config = self.load_config()
        return self._config
