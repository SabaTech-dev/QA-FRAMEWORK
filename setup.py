# QA-FRAMEWORK - Setup Configuration
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="qa-framework",
    version="1.0.0",
    author="Alfred",
    author_email="alfred@example.com",
    description="Modern QA Automation Framework with Clean Architecture and SOLID Principles",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/qa-framework",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.12",
    install_requires=[
        "pytest>=7.4.0",
        "pytest-asyncio>=0.23.0",
        "pytest-xdist>=3.5.0",
        "pytest-cov>=4.1.0",
        "httpx>=0.26.0",
        "requests>=2.31.0",
        "playwright>=1.41.0",
        "pydantic>=2.6.0",
        "pyyaml>=6.0.0",
        "allure-pytest>=2.13.0",
        "faker>=23.0.0",
        "bcrypt>=4.1.0",
        "python-jose[cryptography]>=3.3.0",
        "fastapi>=0.109.0",
    ],
    extras_require={
        "dev": [
            "black>=24.1.0",
            "ruff>=0.2.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
            "PyJWT>=2.8.0",
        ],
        "ui": [
            "selenium>=4.16.0",
        ],
        "performance": [
            "locust>=2.22.0",
        ],
        "security": [
            "bandit>=1.7.0",
            "safety>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "qa-framework=src.core.cli:main",
        ],
    },
)
