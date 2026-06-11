"""
Feature Flags for QA-Framework
System for gradual rollout and A/B testing
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
import hashlib
import json


class FeatureFlagStrategy(str, Enum):
    """Feature flag rollout strategies."""
    PERCENTAGE = "percentage"  # Rollout to X% of users
    USER_LIST = "user_list"  # Rollout to specific users
    USER_SEGMENT = "user_segment"  # Rollout to user segments
    GRADUAL = "gradual"  # Gradual rollout over time
    A_B_TEST = "ab_test"  # A/B testing


class FeatureFlag:
    """
    Feature flag with multiple rollout strategies.
    
    Attributes:
        name: Unique flag identifier
        enabled: Master switch (False = disabled for everyone)
        strategy: Rollout strategy
        config: Strategy-specific configuration
        description: Human-readable description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        name: str,
        enabled: bool = True,
        strategy: FeatureFlagStrategy = FeatureFlagStrategy.PERCENTAGE,
        config: Optional[Dict[str, Any]] = None,
        description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.name = name
        self.enabled = enabled
        self.strategy = strategy
        self.config = config or {}
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def is_enabled_for_user(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if feature is enabled for a specific user.
        
        Args:
            user_id: User identifier
            context: Additional context (user segment, etc.)
            
        Returns:
            True if feature is enabled for this user
        """
        if not self.enabled:
            return False
        
        if self.strategy == FeatureFlagStrategy.PERCENTAGE:
            return self._check_percentage(user_id)
        
        elif self.strategy == FeatureFlagStrategy.USER_LIST:
            return self._check_user_list(user_id)
        
        elif self.strategy == FeatureFlagStrategy.USER_SEGMENT:
            return self._check_user_segment(user_id, context)
        
        elif self.strategy == FeatureFlagStrategy.GRADUAL:
            return self._check_gradual()
        
        elif self.strategy == FeatureFlagStrategy.A_B_TEST:
            return self._check_ab_test(user_id)
        
        return False
    
    def _check_percentage(self, user_id: str) -> bool:
        """Check percentage-based rollout."""
        percentage = self.config.get("percentage", 0)
        
        # Hash user ID to get consistent result
        hash_value = int(hashlib.sha256(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        user_bucket = hash_value % 100
        
        return user_bucket < percentage
    
    def _check_user_list(self, user_id: str) -> bool:
        """Check user list-based rollout."""
        allowed_users = self.config.get("users", [])
        return user_id in allowed_users
    
    def _check_user_segment(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check user segment-based rollout."""
        if not context:
            return False
        
        allowed_segments = self.config.get("segments", [])
        user_segment = context.get("segment")
        
        return user_segment in allowed_segments
    
    def _check_gradual(self) -> bool:
        """Check gradual rollout based on time."""
        start_date = self.config.get("start_date")
        end_date = self.config.get("end_date")
        start_percentage = self.config.get("start_percentage", 0)
        end_percentage = self.config.get("end_percentage", 100)
        
        if not start_date or not end_date:
            return False
        
        start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
        
        now = datetime.utcnow()
        
        if now < start_dt:
            return False
        
        if now > end_dt:
            return end_percentage == 100
        
        # Calculate current percentage based on time progress
        total_duration = (end_dt - start_dt).total_seconds()
        elapsed = (now - start_dt).total_seconds()
        progress = elapsed / total_duration
        
        current_percentage = start_percentage + (end_percentage - start_percentage) * progress
        
        # Use a fixed bucket for gradual (not user-specific)
        current_bucket = int(hashlib.sha256(self.name.encode()).hexdigest(), 16) % 100
        
        return current_bucket < current_percentage
    
    def _check_ab_test(self, user_id: str) -> bool:
        """Check A/B test assignment."""
        variants = self.config.get("variants", ["A", "B"])
        weights = self.config.get("weights", [50, 50])
        
        # Hash user ID to get consistent variant
        hash_value = int(hashlib.sha256(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        bucket = hash_value % 100
        
        # Determine variant based on weights
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if bucket < cumulative:
                # Return True if this is variant B (or the "test" variant)
                return i > 0
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "strategy": self.strategy.value,
            "config": self.config,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureFlag":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            enabled=data["enabled"],
            strategy=FeatureFlagStrategy(data["strategy"]),
            config=data.get("config", {}),
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None
        )


class FeatureFlagManager:
    """
    Manager for feature flags.
    
    Features:
    - Store and retrieve flags
    - Evaluate flags for users
    - Track flag usage
    - Hot reload support
    """
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.evaluation_count: Dict[str, int] = {}
    
    def register_flag(self, flag: FeatureFlag) -> None:
        """Register a feature flag."""
        self.flags[flag.name] = flag
        self.evaluation_count[flag.name] = 0
    
    def unregister_flag(self, name: str) -> bool:
        """Unregister a feature flag."""
        if name in self.flags:
            del self.flags[name]
            del self.evaluation_count[name]
            return True
        return False
    
    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        return self.flags.get(name)
    
    def is_enabled(self, name: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a feature is enabled for a user.
        
        Args:
            name: Flag name
            user_id: User identifier
            context: Additional context
            
        Returns:
            True if feature is enabled
        """
        flag = self.get_flag(name)
        if not flag:
            return False  # Default to disabled for unknown flags
        
        # Track evaluation
        self.evaluation_count[name] = self.evaluation_count.get(name, 0) + 1
        
        return flag.is_enabled_for_user(user_id, context)
    
    def get_all_flags(self) -> List[Dict[str, Any]]:
        """Get all registered flags."""
        return [flag.to_dict() for flag in self.flags.values()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feature flag statistics."""
        return {
            "total_flags": len(self.flags),
            "enabled_flags": sum(1 for f in self.flags.values() if f.enabled),
            "evaluations": dict(self.evaluation_count)
        }
    
    def export_flags(self) -> str:
        """Export all flags as JSON."""
        return json.dumps([flag.to_dict() for flag in self.flags.values()], indent=2)
    
    def import_flags(self, json_str: str) -> int:
        """
        Import flags from JSON.
        
        Returns:
            Number of flags imported
        """
        data = json.loads(json_str)
        count = 0
        
        for flag_data in data:
            flag = FeatureFlag.from_dict(flag_data)
            self.register_flag(flag)
            count += 1
        
        return count


# Global feature flag manager
flag_manager = FeatureFlagManager()


def get_flag_manager() -> FeatureFlagManager:
    """Get global flag manager instance."""
    return flag_manager


# Convenience functions
def is_feature_enabled(name: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """Check if a feature is enabled."""
    return flag_manager.is_enabled(name, user_id, context)


def register_feature_flag(
    name: str,
    enabled: bool = True,
    strategy: FeatureFlagStrategy = FeatureFlagStrategy.PERCENTAGE,
    config: Optional[Dict[str, Any]] = None,
    description: str = ""
) -> FeatureFlag:
    """Register a new feature flag."""
    flag = FeatureFlag(
        name=name,
        enabled=enabled,
        strategy=strategy,
        config=config,
        description=description
    )
    flag_manager.register_flag(flag)
    return flag
