"""
Connection tracking and draining functionality
"""

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.infrastructure.logger.logger import QALogger
from src.infrastructure.shutdown.models import ConnectionInfo, ResourceType, ShutdownConfig

logger = QALogger.get_logger(__name__)


class ConnectionTracker:
    """
    Tracks active connections and requests.

    Provides:
    - Connection registration and deregistration
    - Request tracking per connection
    - Connection draining with timeout
    - Connection statistics
    """

    def __init__(self, config: Optional[ShutdownConfig] = None):
        self.config = config or ShutdownConfig()
        self._connections: Dict[str, ConnectionInfo] = {}
        self._connections_by_type: Dict[ResourceType, List[str]] = defaultdict(list)
        self._request_counter: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._is_accepting_new = True

    async def register_connection(
        self,
        resource_type: ResourceType,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register a new connection.

        Args:
            resource_type: Type of resource (DATABASE, REDIS, HTTP_CLIENT, etc.)
            connection_id: Optional custom connection ID (auto-generated if not provided)
            metadata: Optional metadata about the connection

        Returns:
            Connection ID

        Raises:
            RuntimeError: If not accepting new connections
        """
        async with self._lock:
            if not self._is_accepting_new:
                raise RuntimeError("Not accepting new connections - shutdown in progress")

            conn_id = connection_id or f"{resource_type.value}_{uuid.uuid4().hex[:8]}"

            conn_info = ConnectionInfo(
                connection_id=conn_id,
                resource_type=resource_type,
                created_at=datetime.now(),
                metadata=metadata or {},
                request_count=0,
                is_active=True,
            )

            self._connections[conn_id] = conn_info
            self._connections_by_type[resource_type].append(conn_id)

            logger.debug(
                f"Connection registered: connection_id={conn_id}, resource_type={resource_type.value}"
            )

            return conn_id

    async def deregister_connection(self, connection_id: str) -> bool:
        """
        Deregister a connection.

        Args:
            connection_id: ID of connection to deregister

        Returns:
            True if connection was deregistered, False if not found
        """
        async with self._lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                logger.warning(
                    f"Attempted to deregister unknown connection: connection_id={connection_id}"
                )
                return False

            conn_info.is_active = False

            # Remove from type index
            type_list = self._connections_by_type[conn_info.resource_type]
            if connection_id in type_list:
                type_list.remove(connection_id)

            # Remove from main dict
            del self._connections[connection_id]

            # Clean up request counter
            if connection_id in self._request_counter:
                del self._request_counter[connection_id]

            logger.debug(
                f"Connection deregistered: connection_id={connection_id}, resource_type={conn_info.resource_type.value}"
            )

            return True

    async def start_request(self, connection_id: str) -> bool:
        """
        Mark a request as started on a connection.

        Args:
            connection_id: Connection ID

        Returns:
            True if request was tracked, False if connection not found
        """
        async with self._lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info or not conn_info.is_active:
                return False

            self._request_counter[connection_id] += 1
            conn_info.request_count = self._request_counter[connection_id]

            return True

    async def end_request(self, connection_id: str) -> bool:
        """
        Mark a request as completed on a connection.

        Args:
            connection_id: Connection ID

        Returns:
            True if request was tracked, False if connection not found
        """
        async with self._lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                return False

            if self._request_counter[connection_id] > 0:
                self._request_counter[connection_id] -= 1
                conn_info.request_count = self._request_counter[connection_id]

            return True

    def stop_accepting_new(self):
        """
        Stop accepting new connections.

        This should be called when shutdown begins.
        """
        self._is_accepting_new = False
        logger.info("Stopped accepting new connections")

    def is_accepting_new(self) -> bool:
        """Check if accepting new connections"""
        return self._is_accepting_new

    async def get_active_connections_count(self) -> int:
        """Get count of active connections"""
        async with self._lock:
            return len([c for c in self._connections.values() if c.is_active])

    async def get_in_flight_requests_count(self) -> int:
        """Get total count of in-flight requests"""
        async with self._lock:
            return sum(self._request_counter.values())

    async def get_connections_by_type(self, resource_type: ResourceType) -> List[ConnectionInfo]:
        """Get all connections of a specific type"""
        async with self._lock:
            conn_ids = self._connections_by_type.get(resource_type, [])
            return [
                self._connections[cid]
                for cid in conn_ids
                if cid in self._connections and self._connections[cid].is_active
            ]

    async def get_all_active_connections(self) -> List[ConnectionInfo]:
        """Get all active connections"""
        async with self._lock:
            return [c for c in self._connections.values() if c.is_active]

    async def drain_connections(
        self, timeout: Optional[float] = None, check_interval: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Drain all active connections by waiting for in-flight requests.

        Args:
            timeout: Maximum time to wait for draining
            check_interval: How often to check for completion

        Returns:
            Dict with drain statistics:
            - active_connections: connections that were active
            - remaining_requests: requests still in flight (if timeout)
            - drained_connections: connections that completed
        """
        timeout = timeout or self.config.drain_timeout
        check_interval = check_interval or self.config.drain_check_interval

        # Stop accepting new connections
        self.stop_accepting_new()

        start_time = datetime.now()

        # Get initial counts
        active_conns = await self.get_active_connections_count()
        initial_requests = await self.get_in_flight_requests_count()

        logger.info(
            f"Starting connection drain: active_connections={active_conns}, in_flight_requests={initial_requests}"
        )

        # Wait for requests to complete
        elapsed = 0.0
        while elapsed < timeout:
            in_flight = await self.get_in_flight_requests_count()

            if in_flight == 0:
                logger.info(f"All connections drained successfully: duration_seconds={elapsed}")
                return {
                    "active_connections": active_conns,
                    "remaining_requests": 0,
                    "drained_connections": active_conns,
                }

            logger.debug(
                f"Waiting for requests to complete: in_flight_requests={in_flight}, elapsed_seconds={elapsed}"
            )

            await asyncio.sleep(check_interval)
            elapsed = (datetime.now() - start_time).total_seconds()

        # Timeout reached
        remaining = await self.get_in_flight_requests_count()
        logger.warning(
            f"Connection drain timeout reached: remaining_requests={remaining}, timeout_seconds={timeout}"
        )

        return {
            "active_connections": active_conns,
            "remaining_requests": remaining,
            "drained_connections": active_conns - remaining if remaining < active_conns else 0,
        }

    async def force_close_all(self) -> int:
        """
        Force close all tracked connections.

        Returns:
            Number of connections closed
        """
        async with self._lock:
            count = 0
            for conn_info in list(self._connections.values()):
                if conn_info.is_active:
                    conn_info.is_active = False
                    count += 1

            self._connections.clear()
            self._connections_by_type.clear()
            self._request_counter.clear()

            logger.warning(f"Force closed all connections: count={count}")

            return count

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self._connections),
            "active_connections": len([c for c in self._connections.values() if c.is_active]),
            "accepting_new": self._is_accepting_new,
            "by_type": {rt.value: len(conns) for rt, conns in self._connections_by_type.items()},
            "total_in_flight_requests": sum(self._request_counter.values()),
        }
