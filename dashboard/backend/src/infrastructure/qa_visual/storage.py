"""JSON-file persistence for QA Visual reports.

Follows the GO-NOGO Fase B direction: reports live under ``reports/qa-visual/``
as self-contained JSON documents (same shape as the Fase A spike reports).
The store is an abstraction so the backend can be swapped for SQLite/Postgres
without touching the analyzer or the endpoint (DIP).

Filenames are ``qa_visual_<target>_<report_id>.json`` with the target
sanitised, and the report id is embedded in each document so lookups never
depend on filename parsing.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.infrastructure.qa_visual.models import AnalyzeResponse


def new_report_id() -> str:
    """Generate a unique report id."""
    return uuid.uuid4().hex[:12]


def _sanitize_target(target: str) -> str:
    """Make a target safe for filenames."""
    sanitized = re.sub(r"[^a-z0-9_-]+", "-", target.lower()).strip("-")
    return sanitized or "unknown"


class ReportAccessDenied(Exception):
    """The report exists but is not accessible to the requesting owner (adv-1).

    Raised instead of returning ``None`` so routers can answer 403
    without a second unscoped lookup leaking report existence.
    """


class QAVisualReportStore:
    """Saves and queries QA Visual reports as JSON files."""

    def __init__(self, reports_dir: str):
        self._dir = Path(reports_dir)

    @property
    def reports_dir(self) -> Path:
        return self._dir

    def save(self, response: AnalyzeResponse) -> Path:
        """Persist one report and return its path."""
        self._dir.mkdir(parents=True, exist_ok=True)
        response.report_id = response.report_id or new_report_id()
        if not response.timestamp or response.timestamp.year < 2000:
            response.timestamp = datetime.now(UTC)
        path = (
            self._dir / f"qa_visual_{_sanitize_target(response.target)}_{response.report_id}.json"
        )
        path.write_text(response.model_dump_json(indent=2))
        return path

    def list_reports(
        self,
        target: str | None = None,
        limit: int | None = None,
        owner: str | None = None,
    ) -> list[dict[str, Any]]:
        """List reports (newest first), optionally filtered by target.

        When ``owner`` is given only that owner's reports are returned;
        reports persisted before owner-scoping (owner absent/None) are
        excluded because no regular user owns them.
        """
        reports = []
        for path in self._dir.glob("*.json") if self._dir.exists() else []:
            report = self._read_report(path)
            if report is None:
                continue
            if target and report.get("target") != target:
                continue
            if owner is not None and report.get("owner") != owner:
                continue
            reports.append(report)
        reports.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        return reports[:limit] if limit else reports

    def get_report(
        self,
        report_id: str,
        owner: str | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any] | None:
        """Return one report by id if the caller may read it (adv-1).

        Fail-closed: callers must state who is asking — an explicit
        ``owner`` to scope the read, or ``is_admin=True`` to lift the
        scoping. A call with neither is a programming error, so a new
        caller can never silently read every tenant's reports.

        Returns ``None`` when no report with that id exists; raises
        ``ReportAccessDenied`` when it exists but belongs to another
        owner (legacy unowned reports are admin-only, as everywhere).
        """
        if owner is None and not is_admin:
            raise ValueError(
                "get_report() requires an explicit owner or is_admin=True (fail-closed)"
            )
        for path in self._dir.glob("*.json") if self._dir.exists() else []:
            report = self._read_report(path)
            if report and report.get("report_id") == report_id:
                if is_admin or report.get("owner") == owner:
                    return report
                raise ReportAccessDenied(report_id)
        return None

    def get_baseline(self, target: str, owner: str | None = None) -> dict[str, Any] | None:
        """Return the earliest report for a target (its visual baseline).

        With ``owner`` the baseline is scoped to that owner so scores are
        never compared across owners (S-1R).
        """
        reports = self.list_reports(target=target, owner=owner)
        if not reports:
            return None
        return min(reports, key=lambda r: r.get("timestamp") or "")

    @staticmethod
    def _read_report(path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
