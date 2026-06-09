"""
Query Optimizer - Database Query Optimization Utilities

Provides:
- Query analysis and optimization suggestions
- Query caching for frequent queries
- Connection pooling configuration
- Slow query logging
"""

import time
import functools
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Engine
import structlog

logger = structlog.get_logger()


class QueryOptimizer:
    """Database query optimizer and analyzer"""
    
    def __init__(self, engine: Engine, slow_query_threshold: float = 0.1):
        """
        Initialize query optimizer
        
        Args:
            engine: SQLAlchemy engine
            slow_query_threshold: Threshold in seconds for slow query logging (default: 100ms)
        """
        self.engine = engine
        self.slow_query_threshold = slow_query_threshold
        self.slow_queries: List[Dict[str, Any]] = []
        
        # Set up event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for query profiling"""
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries"""
            total_time = time.time() - conn.info['query_start_time'].pop()
            
            if total_time > self.slow_query_threshold:
                self.slow_queries.append({
                    'query': statement,
                    'parameters': parameters,
                    'duration': total_time,
                    'timestamp': time.time()
                })
                
                logger.warning(
                    "Slow query detected",
                    query=statement[:200],  # Truncate long queries
                    duration=total_time,
                    threshold=self.slow_query_threshold
                )
    
    def get_slow_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of slow queries
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of slow query records
        """
        return self.slow_queries[-limit:]
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query for optimization opportunities
        
        Args:
            query: SQL query to analyze
        
        Returns:
            Analysis results with suggestions
        """
        suggestions = []
        
        # Check for SELECT *
        if "SELECT *" in query.upper():
            suggestions.append({
                'type': 'performance',
                'message': 'Avoid SELECT * - specify required columns',
                'severity': 'medium'
            })
        
        # Check for missing WHERE clause
        if "WHERE" not in query.upper() and ("SELECT" in query.upper() or "UPDATE" in query.upper() or "DELETE" in query.upper()):
            suggestions.append({
                'type': 'safety',
                'message': 'No WHERE clause - may affect all rows',
                'severity': 'high'
            })
        
        # Check for LIKE with leading wildcard
        if "LIKE '%" in query.upper():
            suggestions.append({
                'type': 'performance',
                'message': 'LIKE with leading wildcard prevents index usage',
                'severity': 'medium'
            })
        
        # Check for ORDER BY on non-indexed columns (simplified check)
        if "ORDER BY" in query.upper():
            suggestions.append({
                'type': 'performance',
                'message': 'Ensure ORDER BY columns have indexes',
                'severity': 'low'
            })
        
        return {
            'query': query,
            'suggestions': suggestions,
            'suggestion_count': len(suggestions)
        }
    
    async def get_table_stats(self, session: AsyncSession, table_name: str) -> Dict[str, Any]:
        """
        Get statistics for a table
        
        Args:
            session: Database session
            table_name: Name of the table
        
        Returns:
            Table statistics
        """
        # Get row count
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        row_count = result.scalar()
        
        # Get table size (PostgreSQL)
        result = await session.execute(text(f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))"))
        table_size = result.scalar()
        
        return {
            'table_name': table_name,
            'row_count': row_count,
            'size': table_size
        }
    
    async def get_index_usage(self, session: AsyncSession, table_name: str) -> List[Dict[str, Any]]:
        """
        Get index usage statistics for a table
        
        Args:
            session: Database session
            table_name: Name of the table
        
        Returns:
            Index usage statistics
        """
        query = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_tup_read,
                idx_tup_fetch,
                idx_scan
            FROM pg_stat_user_indexes
            WHERE tablename = :table_name
            ORDER BY idx_scan DESC
        """)
        
        result = await session.execute(query, {'table_name': table_name})
        rows = result.fetchall()
        
        return [
            {
                'schema': row[0],
                'table': row[1],
                'index': row[2],
                'tuples_read': row[3],
                'tuples_fetched': row[4],
                'index_scans': row[5]
            }
            for row in rows
        ]


class QueryCache:
    """Simple in-memory cache for query results"""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize query cache
        
        Args:
            ttl: Time-to-live in seconds (default: 5 minutes)
            max_size: Maximum number of cached items
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _hash_query(self, query: str, params: tuple = ()) -> str:
        """Generate hash for query and parameters"""
        import hashlib
        content = f"{query}:{params}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """
        Get cached result
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            Cached result or None
        """
        key = self._hash_query(query, params)
        
        if key in self._cache:
            item = self._cache[key]
            
            # Check if expired
            if time.time() - item['timestamp'] < self.ttl:
                return item['result']
            else:
                del self._cache[key]
        
        return None
    
    def set(self, query: str, result: Any, params: tuple = ()):
        """
        Cache query result
        
        Args:
            query: SQL query
            result: Query result to cache
            params: Query parameters
        """
        # Evict oldest if at max size
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
        
        key = self._hash_query(query, params)
        self._cache[key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear cache"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'ttl': self.ttl
        }


def cached_query(ttl: int = 300):
    """
    Decorator to cache query results
    
    Usage:
        @cached_query(ttl=60)
        async def get_user(user_id: int):
            ...
    """
    cache = QueryCache(ttl=ttl)
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result)
            
            return result
        
        return wrapper
    
    return decorator


# Global query cache instance
query_cache = QueryCache()
