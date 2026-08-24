"""
Data models for shutdown management
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ShutdownPhase(Enum):
    """Shutdown phases in order"""

    NONE = "none"
    INITIATED = "initiated"
    STOPPING_NEW_REQUESTS = "stopping_new_requests"
    DRAINING_CONNECTIONS = "draining_connections"
    CLOSING_RESOURCES = "closing_resources"
    FLUSHING_BUFFERS = "flushing_buffers"
    COMPLETED = "completed"
    FORCED = "forced"


class ResourceType(Enum):
    """Types of resources to manage during shutdown"""

    DATABASE = "database"
    REDIS = "redis"
    HTTP_CLIENT = "http_client"
    FILE_HANDLE = "file_handle"
    CUSTOM = "custom"


class ShutdownStatus(Enum):
    """Overall shutdown status"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ConnectionInfo:
    """Information about an active connection"""

    connection_id: str
    resource_type: ResourceType
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_count: int = 0
    is_active: bool = True


@dataclass
class ResourceInfo:
    """Information about a managed resource"""

    name: str
    resource_type: ResourceType
    instance: Any
    close_handler: Optional[str] = None  # Name of method to call for closing
    priority: int = 100  # Lower = closed first
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShutdownProgress:
    """Tracks shutdown progress"""

    phase: ShutdownPhase = ShutdownPhase.NONE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    active_connections: int = 0
    drained_connections: int = 0
    closed_resources: int = 0
    total_resources: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate shutdown duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        """Check if shutdown is complete"""
        return self.phase in [ShutdownPhase.COMPLETED, ShutdownPhase.FORCED]


@dataclass
class ShutdownConfig:
    """Configuration for shutdown behavior"""

    # Timeouts
    graceful_timeout: float = 30.0  # Total time for graceful shutdown
    drain_timeout: float = 10.0  # Time to drain connections
    resource_close_timeout: float = 5.0  # Time per resource to close

    # Connection draining
    drain_check_interval: float = 0.5  # How often to check connections
    max_in_flight_requests: int = 1000  # Max requests to track

    # Behavior
    force_after_timeout: bool = True  # Force shutdown after timeout
    log_progress: bool = True  # Log shutdown progress
    raise_on_error: bool = False  # Raise exceptions during shutdown

    # Callbacks
    pre_shutdown_hooks: List[str] = field(default_factory=list)
    post_shutdown_hooks: List[str] = field(default_factory=list)


@dataclass
class ShutdownResult:
    """Result of shutdown operation"""

    status: ShutdownStatus
    progress: ShutdownProgress
    message: str = ""

    @property
    def success(self) -> bool:
        """Check if shutdown was successful"""
        return self.status in [ShutdownStatus.SUCCESSFUL, ShutdownStatus.IN_PROGRESS]
