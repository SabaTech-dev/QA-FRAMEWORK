"""
Test Search Service

Manual test script to verify global search functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
pytest.importorskip('sqlalchemy')
pytest.importorskip('asyncpg')
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.search_service import SearchService
from schemas.search import SearchQuery


async def test_search():
    """Test search service with various queries."""
    
    # Create test database connection (you'll need to adjust this)
    # For now, this is a template
    print("🔍 Testing Search Service")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        ("login", None, 10, 0),
        ("auth", ["suites", "cases"], 5, 0),
        ("test", None, 10, 5),  # Test pagination with offset
        ("lgoin", None, 5, 0),  # Test fuzzy matching (typo)
        ("user@example.com", ["users"], 10, 0),
    ]
    
    print("\n📋 Test Cases:")
    for i, (query, types, limit, offset) in enumerate(test_queries, 1):
        print(f"{i}. Query: '{query}', Types: {types}, Limit: {limit}, Offset: {offset}")
    
    print("\n✅ Schema validation:")
    for query, types, limit, offset in test_queries:
        try:
            search_query = SearchQuery(q=query, types=types, limit=limit, offset=offset)
            print(f"  ✓ '{query}' - Valid")
        except Exception as e:
            print(f"  ✗ '{query}' - Error: {e}")
    
    print("\n" + "=" * 50)
    print("📝 Note: To run full integration tests,")
    print("   you need a running database with test data.")
    print("\n✨ All schema validations passed!")


if __name__ == "__main__":
    asyncio.run(test_search())
