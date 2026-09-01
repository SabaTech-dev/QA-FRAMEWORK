"""Utility-criterion checker: evaluates the scenario's utility_criterion
against the isolated workspace filesystem. Fails closed on unsupported
criteria."""

from pathlib import Path


class UtilityChecker:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def check(self, criterion: str) -> bool:
        supported = " exists and is non-empty"
        if criterion.endswith(supported):
            rel_path = criterion[: -len(supported)].strip()
            target = self.workspace / rel_path
            return target.is_file() and target.stat().st_size > 0
        # Unknown criterion: fail closed (never assume utility).
        return False
