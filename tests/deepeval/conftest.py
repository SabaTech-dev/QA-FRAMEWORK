"""Shared fixtures for DeepEval trajectory tests.

Provides golden-path trajectories and mock agent trajectories for testing.

Card: 7e4a76ee-0061-44ce-97c2-d418b461583a
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from qa_framework.evaluation.trajectory import (
    ToolCall,
    Trajectory,
    TrajectoryComparator,
)

# ── DeepEval graceful import guard ──────────────────────────────
try:
    from deepeval.metrics import GEval, TaskCompletionMetric
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


# =============================================================================
# GOLDEN TRAJECTORIES — expected optimal agent behavior
# =============================================================================

GOLDEN_TRAJECTORIES = {
    "test_execution": Trajectory(
        task="Run the regression test suite",
        tool_calls=[
            ToolCall("select_adapter", {"adapter": "pytest"}),
            ToolCall("execute_tests", {"suite": "regression"}, result={"passed": 45, "failed": 2}),
            ToolCall("report_results", {"format": "json"}, result={"report": "generated"}),
        ],
        final_answer="Regression suite completed: 45 passed, 2 failed.",
    ),
    "bug_report": Trajectory(
        task="Report a failing test as a bug",
        tool_calls=[
            ToolCall("capture_error", {"test_id": "test_login"}, result={"traceback": "..."}),
            ToolCall("create_bug_report", {"title": "Login fails", "severity": "high"}, result={"bug_id": "BUG-001"}),
            ToolCall("link_to_test", {"bug_id": "BUG-001", "test_id": "test_login"}),
        ],
        final_answer="Bug BUG-001 created and linked to test_login.",
    ),
    "coverage_analysis": Trajectory(
        task="Analyze test coverage and suggest improvements",
        tool_calls=[
            ToolCall("run_coverage", {"suite": "all"}, result={"coverage": 72.5}),
            ToolCall("generate_report", {"format": "html"}),
            ToolCall("suggest_improvements", {"uncovered": ["utils.py"]}),
        ],
        final_answer="Coverage 72.5%. Suggestion: add tests for utils.py.",
    ),
    "parallel_execution": Trajectory(
        task="Run tests in parallel",
        tool_calls=[
            ToolCall("split_suite", {"workers": 4}, result={"chunks": 4}),
            ToolCall("execute_parallel", {"chunks": 4}, result={"all_passed": True}),
            ToolCall("merge_results", {"chunks": 4}, result={"total": 120, "passed": 118}),
        ],
        final_answer="Parallel run complete: 118/120 passed across 4 workers.",
    ),
    "screenshot_capture": Trajectory(
        task="Capture screenshot on test failure",
        tool_calls=[
            ToolCall("detect_failure", {"test_id": "test_ui"}, result={"failed": True}),
            ToolCall("capture_screenshot", {"test_id": "test_ui"}, result={"path": "/tmp/ss.png"}),
            ToolCall("attach_to_report", {"report_id": "R1", "path": "/tmp/ss.png"}),
        ],
        final_answer="Screenshot captured and attached to report R1.",
    ),
    "retry_flaky": Trajectory(
        task="Retry a flaky test up to 3 times",
        tool_calls=[
            ToolCall("run_test", {"test_id": "test_flaky"}, result={"outcome": "failed"}, success=False),
            ToolCall("run_test", {"test_id": "test_flaky", "retry": 1}, result={"outcome": "failed"}, success=False),
            ToolCall("run_test", {"test_id": "test_flaky", "retry": 2}, result={"outcome": "passed"}),
            ToolCall("mark_flaky", {"test_id": "test_flaky", "retries": 2}),
        ],
        final_answer="Test test_flaky marked as flaky (passed on retry 2).",
    ),
    "cross_browser": Trajectory(
        task="Run tests across multiple browsers",
        tool_calls=[
            ToolCall("select_browser", {"browser": "chromium"}, result={"status": "ok"}),
            ToolCall("select_browser", {"browser": "firefox"}, result={"status": "ok"}),
            ToolCall("select_browser", {"browser": "webkit"}, result={"status": "ok"}),
            ToolCall("aggregate_results", {"browsers": 3}, result={"all_passed": True}),
        ],
        final_answer="Cross-browser tests passed on all 3 browsers.",
    ),
    "api_test": Trajectory(
        task="Test the user API endpoint",
        tool_calls=[
            ToolCall("http_request", {"method": "GET", "url": "/api/users"}, result={"status": 200}),
            ToolCall("validate_schema", {"response": "...", "schema": "user_list"}),
            ToolCall("report_results", {"format": "json"}),
        ],
        final_answer="API test passed: schema valid, 200 OK.",
    ),
    "performance_test": Trajectory(
        task="Run performance benchmarks and compare to baseline",
        tool_calls=[
            ToolCall("run_perf_suite", {"suite": "load_test"}, result={"p95": 120}),
            ToolCall("get_baseline", {"name": "v1.0"}, result={"p95": 150}),
            ToolCall("compare_metrics", {"current": 120, "baseline": 150}, result={"improvement": "20%"}),
        ],
        final_answer="Performance improved 20% vs baseline (p95: 120ms vs 150ms).",
    ),
    "ci_cd_integration": Trajectory(
        task="Run smoke tests and gate deployment",
        tool_calls=[
            ToolCall("receive_trigger", {"event": "push", "branch": "main"}),
            ToolCall("run_smoke_tests", {"suite": "smoke"}, result={"passed": 10, "failed": 0}),
            ToolCall("gate_deployment", {"result": "pass"}, result={"deploy": True}),
        ],
        final_answer="Smoke tests passed. Deployment gated for production.",
    ),
}


# =============================================================================
# AGENT TRAJECTORIES — mock agent execution (for comparison testing)
# =============================================================================

AGENT_PERFECT = {key: traj for key, traj in GOLDEN_TRAJECTORIES.items()}

AGENT_WITH_ERRORS = {
    "test_execution": Trajectory(
        task="Run the regression test suite",
        tool_calls=[
            ToolCall("select_adapter", {"adapter": "pytest"}),
            ToolCall("execute_tests", {"suite": "regression"}, result=None, success=False),
            ToolCall("report_results", {"format": "json"}),
        ],
        final_answer="Regression suite completed with 1 error.",
    ),
}

AGENT_WRONG_TOOLS = {
    "test_execution": Trajectory(
        task="Run the regression test suite",
        tool_calls=[
            ToolCall("wrong_tool", {}),
            ToolCall("another_wrong", {}),
        ],
        final_answer="",
    ),
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def golden_trajectory():
    """Return a factory that fetches golden trajectories by name."""
    def _get(name: str) -> Trajectory:
        if name not in GOLDEN_TRAJECTORIES:
            raise KeyError(f"Unknown golden trajectory: {name}. Available: {list(GOLDEN_TRAJECTORIES.keys())}")
        return GOLDEN_TRAJECTORIES[name]
    return _get


@pytest.fixture
def agent_trajectory():
    """Return a factory that fetches mock agent trajectories by name."""
    def _get(name: str, variant: str = "perfect") -> Trajectory:
        if variant == "perfect":
            source = AGENT_PERFECT
        elif variant == "errors":
            source = AGENT_WITH_ERRORS
        elif variant == "wrong":
            source = AGENT_WRONG_TOOLS
        else:
            raise ValueError(f"Unknown variant: {variant}")
        if name not in source:
            raise KeyError(f"Unknown trajectory: {name}")
        return source[name]
    return _get


@pytest.fixture
def comparator(golden_trajectory):
    """Return a factory that creates TrajectoryComparators."""
    def _make(golden_name: str) -> TrajectoryComparator:
        return TrajectoryComparator(golden_trajectory(golden_name))
    return _make
