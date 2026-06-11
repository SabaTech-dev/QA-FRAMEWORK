"""
Smart Cache with Intelligent Invalidation for QA-Framework
Advanced caching system with TTL, event-based, and dependency-based invalidation
"""

import redis
import json
import hashlib
from typing import Any, Optional, List, Set, Dict
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"  # Time-based
    EVENT = "event"  # Event-based
    DEPENDENCY = "dependency"  # Dependency-based
    MANUAL = "manual"  # Manual invalidation


class CacheConfig:
    """Cache configuration for different data types."""
    
    # Test results: 1 hour TTL, invalidate on re-run
    TEST_RESULTS = {
        "ttl": 3600,  # 1 hour
        "strategy": CacheStrategy.TTL,
        "tags": ["test", "result"]
    }
    
    # Test suites: 5 minutes TTL, invalidate on update
    TEST_SUITES = {
        "ttl": 300,  # 5 minutes
        "strategy": CacheStrategy.EVENT,
        "tags": ["suite", "metadata"]
    }
    
    # User data: 30 minutes TTL, invalidate on change
    USER_DATA = {
        "ttl": 1800,  # 30 minutes
        "strategy": CacheStrategy.EVENT,
        "tags": ["user"]
    }
    
    # Dashboard stats: 1 minute TTL, invalidate on event
    DASHBOARD_STATS = {
        "ttl": 60,  # 1 minute
        "strategy": CacheStrategy.EVENT,
        "tags": ["dashboard", "stats"]
    }
    
    # API responses: 10 minutes TTL
    API_RESPONSES = {
        "ttl": 600,  # 10 minutes
        "strategy": CacheStrategy.TTL,
        "tags": ["api"]
    }


class SmartCache:
    """
    Smart cache with intelligent invalidation.
    
    Features:
    - Multiple invalidation strategies (TTL, event, dependency, manual)
    - Cache tags for grouped invalidation
    - Cache warming on startup
    - Cache statistics
    - Stampede protection
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=db, decode_responses=True)
        self.stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "sets": 0
        }
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key from prefix and identifier."""
        key_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"qa:{prefix}:{key_hash}"
    
    def _generate_tags_key(self, tag: str) -> str:
        """Generate key for tag index."""
        return f"qa:tags:{tag}"
    
    def _generate_dependencies_key(self, key: str) -> str:
        """Generate key for dependency tracking."""
        return f"qa:deps:{key}"
    
    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            prefix: Cache category prefix
            identifier: Unique identifier for the value
            
        Returns:
            Cached value or None if not found
        """
        key = self._generate_key(prefix, identifier)
        
        value = self.redis.get(key)
        if value:
            self.stats["hits"] += 1
            return json.loads(value)
        
        self.stats["misses"] += 1
        return None
    
    def set(
        self,
        prefix: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None
    ) -> bool:
        """
        Set value in cache with optional tags and dependencies.
        
        Args:
            prefix: Cache category prefix
            identifier: Unique identifier for the value
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (optional)
            tags: Tags for grouped invalidation (optional)
            dependencies: Other cache keys this depends on (optional)
            
        Returns:
            True if successful
        """
        key = self._generate_key(prefix, identifier)
        
        # Serialize value
        serialized = json.dumps(value, default=str)
        
        # Get TTL from config if not provided
        if ttl is None:
            config = CacheConfig.__dict__.get(prefix.upper(), {})
            ttl = config.get("ttl", 300)  # Default 5 minutes
        
        # Set value with TTL
        if ttl > 0:
            self.redis.setex(key, ttl, serialized)
        else:
            self.redis.set(key, serialized)
        
        self.stats["sets"] += 1
        
        # Add to tag indexes
        if tags:
            for tag in tags:
                self.redis.sadd(self._generate_tags_key(tag), key)
        
        # Track dependencies
        if dependencies:
            for dep_key in dependencies:
                self.redis.sadd(self._generate_dependencies_key(key), dep_key)
        
        return True
    
    def invalidate(self, prefix: str, identifier: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            prefix: Cache category prefix
            identifier: Unique identifier for the value
            
        Returns:
            True if key was deleted
        """
        key = self._generate_key(prefix, identifier)
        
        # Delete dependencies tracking
        deps_key = self._generate_dependencies_key(key)
        self.redis.delete(deps_key)
        
        # Delete the key
        result = self.redis.delete(key)
        
        if result:
            self.stats["invalidations"] += 1
        
        return result > 0
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            Number of keys invalidated
        """
        tags_key = self._generate_tags_key(tag)
        keys = self.redis.smembers(tags_key)
        
        count = 0
        for key in keys:
            if self.redis.delete(key):
                count += 1
                self.stats["invalidations"] += 1
        
        # Clear the tag set
        self.redis.delete(tags_key)
        
        return count
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        Invalidate all cache entries with any of the specified tags.
        
        Args:
            tags: List of tags to invalidate
            
        Returns:
            Number of keys invalidated
        """
        total = 0
        for tag in tags:
            total += self.invalidate_by_tag(tag)
        return total
    
    def invalidate_dependent(self, prefix: str, identifier: str) -> int:
        """
        Invalidate all cache entries that depend on this key.
        
        Args:
            prefix: Cache category prefix
            identifier: Unique identifier for the value
            
        Returns:
            Number of keys invalidated
        """
        key = self._generate_key(prefix, identifier)
        deps_key = self._generate_dependencies_key(key)
        
        # Find all keys that depend on this one
        dependent_keys = set()
        for pattern in self.redis.scan_iter(f"qa:deps:*"):
            deps = self.redis.smembers(pattern)
            if key in deps:
                dependent_keys.add(pattern.replace("qa:deps:", ""))
        
        # Invalidate dependent keys
        count = 0
        for dep_key in dependent_keys:
            if self.redis.delete(dep_key):
                count += 1
                self.stats["invalidations"] += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        # Get memory usage
        memory_info = self.redis.info("memory")
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "invalidations": self.stats["invalidations"],
            "sets": self.stats["sets"],
            "hit_rate_percent": round(hit_rate, 2),
            "memory_used_bytes": memory_info.get("used_memory", 0),
            "memory_used_human": memory_info.get("used_memory_human", "unknown")
        }
    
    def warm_cache(self, data: Dict[str, Any], config: Dict[str, Any]) -> int:
        """
        Warm cache with initial data.
        
        Args:
            data: Dictionary of {identifier: value} pairs
            config: Cache configuration (ttl, tags, etc.)
            
        Returns:
            Number of keys cached
        """
        count = 0
        prefix = config.get("prefix", "default")
        ttl = config.get("ttl", 300)
        tags = config.get("tags", [])
        
        for identifier, value in data.items():
            if self.set(prefix, identifier, value, ttl=ttl, tags=tags):
                count += 1
        
        return count
    
    def clear_all(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful
        """
        # Find all QA cache keys
        keys_deleted = 0
        for key in self.redis.scan_iter("qa:*"):
            if self.redis.delete(key):
                keys_deleted += 1
                self.stats["invalidations"] += 1
        
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check cache health.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Test connection
            self.redis.ping()
            
            # Get stats
            stats = self.get_stats()
            
            return {
                "status": "healthy",
                "connected": True,
                "stats": stats
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Create global cache instance
cache = SmartCache()


def get_cache() -> SmartCache:
    """Get global cache instance."""
    return cache
