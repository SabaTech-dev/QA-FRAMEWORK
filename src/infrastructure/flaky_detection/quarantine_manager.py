"""
Quarantine Manager Implementation

Manages quarantined tests and their evaluation.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from src.domain.flaky_detection.entities import QuarantineEntry, TestRun
from src.domain.flaky_detection.value_objects import QuarantineReason, TestIdentifier


class InMemoryQuarantineManager:
    """
    In-memory implementation of quarantine manager.

    Suitable for development and testing.
    For production, use a database-backed implementation.
    """

    def __init__(self, default_expiry_days: int = 30):
        self.default_expiry_days = default_expiry_days
        self._quarantines: Dict[str, QuarantineEntry] = {}
        self._by_test: Dict[str, str] = {}  # test_id -> quarantine_id

    async def quarantine(
        self,
        test_identifier: TestIdentifier,
        reason: QuarantineReason,
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> QuarantineEntry:
        """Quarantine a flaky test."""
        test_id = str(test_identifier)

        # Check if already quarantined
        if test_id in self._by_test:
            existing_id = self._by_test[test_id]
            return self._quarantines[existing_id]

        # Calculate expiry
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        elif self.default_expiry_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.default_expiry_days)

        entry = QuarantineEntry(
            id=str(uuid4()),
            test_identifier=test_identifier,
            reason=reason,
            description=description,
            quarantined_at=datetime.now(timezone.utc),
            quarantined_by="system",
            expires_at=expires_at,
            tenant_id=None,
        )

        self._quarantines[entry.id] = entry
        self._by_test[test_id] = entry.id

        return entry

    async def release(
        self,
        test_identifier: TestIdentifier,
        notes: Optional[str] = None,
    ) -> Optional[QuarantineEntry]:
        """Release a test from quarantine."""
        test_id = str(test_identifier)

        if test_id not in self._by_test:
            return None

        entry_id = self._by_test[test_id]
        entry = self._quarantines.get(entry_id)

        if entry:
            resolved = entry.resolve(notes)
            self._quarantines[entry_id] = resolved
            del self._by_test[test_id]
            return resolved

        return None

    async def get_quarantined(
        self,
        tenant_id: str,
    ) -> List[QuarantineEntry]:
        """Get all quarantined tests for a tenant."""
        return [
            entry
            for entry in self._quarantines.values()
            if not entry.is_resolved and entry.tenant_id == tenant_id
        ]

    async def evaluate(
        self,
        test_identifier: TestIdentifier,
        recent_runs: List[TestRun],
    ) -> Optional[QuarantineEntry]:
        """
        Evaluate if a quarantined test can be released.

        Criteria for release:
        - At least 10 consecutive passes
        - No failures in recent runs
        """
        test_id = str(test_identifier)

        if test_id not in self._by_test:
            return None

        entry_id = self._by_test[test_id]
        entry = self._quarantines.get(entry_id)

        if not entry:
            return None

        # Check recent runs
        if len(recent_runs) < 10:
            # Not enough data to evaluate
            return entry.add_evaluation(False, "Not enough runs to evaluate")

        # Check for consecutive passes
        consecutive_passes = 0
        for run in reversed(recent_runs):
            if run.passed:
                consecutive_passes += 1
            else:
                break

        if consecutive_passes >= 10:
            # Test appears stable, can be released
            return entry.add_evaluation(True, f"{consecutive_passes} consecutive passes")

        return entry.add_evaluation(False, f"Only {consecutive_passes} consecutive passes")

    async def get_expired(self) -> List[QuarantineEntry]:
        """Get quarantined tests that have expired."""
        return [
            entry
            for entry in self._quarantines.values()
            if entry.is_expired and not entry.is_resolved
        ]

    async def get_all(self) -> List[QuarantineEntry]:
        """Get all quarantine entries."""
        return list(self._quarantines.values())

    def clear(self) -> None:
        """Clear all quarantine data."""
        self._quarantines.clear()
        self._by_test.clear()
