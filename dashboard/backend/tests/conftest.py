"""
Pytest configuration and fixtures

This file configures pytest to work with the backend module structure.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import MagicMock

# Mock Redis to avoid connection errors during import
_mock_redis = MagicMock()
_mock_redis.Redis = MagicMock(return_value=MagicMock(ping=MagicMock(return_value=True)))
_mock_redis.from_url = MagicMock(return_value=MagicMock(ping=MagicMock(return_value=True)))
sys.modules.setdefault("redis", _mock_redis)
sys.modules.setdefault("redis.asyncio", MagicMock())

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure the backend module can be imported
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load environment variables from .env files
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from: {env_file}")
else:
    # Try project root .env
    project_root = backend_dir.parent.parent
    root_env = project_root / ".env"
    if root_env.exists():
        load_dotenv(root_env)
        print(f"Loaded environment from: {root_env}")

# Set Railway Redis URL if not already set (fallback for CI/testing)
if not os.getenv("REDIS_URL"):
    railway_redis = "redis://default:ygZpOipKeuDfOvlxRPrRNGxxeJKsPrPD@centerbeam.proxy.rlwy.net:20994"
    os.environ["REDIS_URL"] = railway_redis
    print("Using Railway Redis URL for testing")

print(f"Backend directory: {backend_dir}")
print(f"Python path: {sys.path[:3]}")  # Show first 3 paths

# Configure logging before any tests run
from core.logging_config import configure_logging
configure_logging(log_level="WARNING", environment="test")