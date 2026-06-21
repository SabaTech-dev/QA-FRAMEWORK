"""Trajectory Evaluation Metrics — 10 test cases covering QA-FRAMEWORK golden paths.

Each test case models an agent trajectory (sequence of tool calls → final answer)
and verifies it against the golden path using TrajectoryComparator metrics.

Target metrics:
    - Tool Accuracy > 85%
    - Tool Error Rate < 5%
    - Success Rate > 85%

Usage:
    pytest tests/deepeval/test_trajectory_metrics.py -v
    pytest tests/deepeval/test_trajectory_metrics.py -k "test_execution" -v

Card: 7e4a76ee-0061-44ce-97c2-d418b461583a
"""

import pytest

from qa_framework.evaluation.trajectory import (
    ToolCall,
    Trajectory,
    TrajectoryComparator,
)


# =============================================================================
# METRIC THRESHOLDS
# =============================================================================

TOOL_ACCURACY_THRESHOLD = 0.85
TOOL_ERROR_RATE_THRESHOLD = 0.05
SUCCESS_RATE_THRESHOLD = 0.85
OVERALL_SCORE_THRESHOLD = 0.85


# =============================================================================
# 1. TEST EXECUTION FLOW
# =============================================================================

class TestTestExecutionFlow:
    """Golden path: user requests test run → agent selects adapter → executes → reports."""

    def test_perfect_trajectory_scores_high(self, comparator, agent_trajectory):
        """Perfect agent trajectory must score above all thresholds."""
        comp = comparator("test_execution")
        agent = agent_trajectory("test_execution", variant="perfect")

        assert comp.tool_accuracy(agent) >= TOOL_ACCURACY_THRESHOLD
        assert comp.tool_error_rate(agent) <= TOOL_ERROR_RATE_THRESHOLD
        assert agent.success_rate >= SUCCESS_RATE_THRESHOLD
        assert comp.overall_score(agent) >= OVERALL_SCORE_THRESHOLD

    def test_trajectory_with_error_flagged(self, comparator, agent_trajectory):
        """Agent with a failed tool call must have high error rate."""
        comp = comparator("test_execution")
        agent = agent_trajectory("test_execution", variant="errors")

        assert comp.tool_error_rate(agent) > TOOL_ERROR_RATE_THRESHOLD


# =============================================================================
# 2. BUG REPORT FLOW
# =============================================================================

class TestBugReportFlow:
    """Golden path: test fails → agent captures error → creates bug → links to test."""

    def test_bug_report_trajectory_tool_accuracy(self, comparator, agent_trajectory):
        """Agent must use the correct tools in the correct order."""
        comp = comparator("bug_report")
        agent = agent_trajectory("bug_report", variant="perfect")

        assert comp.tool_accuracy(agent) == 1.0, (
            f"Expected 100% tool accuracy, got {comp.tool_accuracy(agent)}"
        )
        assert comp.task_completion_score(agent) == 1.0


# =============================================================================
# 3. COVERAGE ANALYSIS FLOW
# =============================================================================

class TestCoverageAnalysisFlow:
    """Golden path: agent runs tests → collects coverage → generates report."""

    def test_coverage_analysis_completes(self, comparator, agent_trajectory):
        """Coverage analysis must complete all 3 tool calls."""
        comp = comparator("coverage_analysis")
        agent = agent_trajectory("coverage_analysis", variant="perfect")

        assert agent.tool_count == 3
        assert comp.overall_score(agent) >= OVERALL_SCORE_THRESHOLD
        report = comp.detailed_report(agent)
        assert report["tool_accuracy"] == 1.0
        assert report["tool_error_rate"] == 0.0


# =============================================================================
# 4. PARALLEL EXECUTION FLOW
# =============================================================================

class TestParallelExecutionFlow:
    """Golden path: split suite → run parallel → merge results."""

    def test_parallel_execution_order_fidelity(self, comparator, agent_trajectory):
        """Agent must preserve the golden ordering for parallel execution."""
        comp = comparator("parallel_execution")
        agent = agent_trajectory("parallel_execution", variant="perfect")

        assert comp.tool_order_fidelity(agent) == 1.0
        assert comp.tool_accuracy(agent) >= TOOL_ACCURACY_THRESHOLD


# =============================================================================
# 5. SCREENSHOT CAPTURE FLOW
# =============================================================================

class TestScreenshotCaptureFlow:
    """Golden path: detect failure → capture screenshot → attach to report."""

    def test_screenshot_capture_tool_sequence(self, comparator, agent_trajectory):
        """Verify the 3-step screenshot flow matches golden path."""
        comp = comparator("screenshot_capture")
        agent = agent_trajectory("screenshot_capture", variant="perfect")

        tool_names = [tc.tool_name for tc in agent.tool_calls]
        assert tool_names == ["detect_failure", "capture_screenshot", "attach_to_report"]
        assert comp.overall_score(agent) >= OVERALL_SCORE_THRESHOLD


# =============================================================================
# 6. RETRY ON FLAKY TEST
# =============================================================================

class TestRetryFlakyTest:
    """Golden path: fail → retry → retry → pass → mark flaky."""

    def test_retry_trajectory_success_rate(self, comparator, agent_trajectory):
        """Even with retries, success rate must be reasonable."""
        comp = comparator("retry_flaky")
        agent = agent_trajectory("retry_flaky", variant="perfect")

        # 4 tool calls, 2 failed (first 2 retries), 2 succeeded
        # success_rate = 2/4 = 0.5 — but task completed
        assert agent.tool_count == 4
        assert agent.error_count == 2  # first 2 attempts failed
        assert comp.task_completion_score(agent) == 1.0  # final_answer present

        # Tool accuracy should still be high (correct tools in correct order)
        assert comp.tool_accuracy(agent) >= TOOL_ACCURACY_THRESHOLD


# =============================================================================
# 7. CROSS-BROWSER FLOW
# =============================================================================

class TestCrossBrowserFlow:
    """Golden path: iterate browsers → aggregate results."""

    def test_cross_browser_all_tools_correct(self, comparator, agent_trajectory):
        """Cross-browser flow must use select_browser × 3 + aggregate."""
        comp = comparator("cross_browser")
        agent = agent_trajectory("cross_browser", variant="perfect")

        browser_tools = [tc for tc in agent.tool_calls if tc.tool_name == "select_browser"]
        assert len(browser_tools) == 3, f"Expected 3 browser selections, got {len(browser_tools)}"
        assert comp.overall_score(agent) >= OVERALL_SCORE_THRESHOLD


# =============================================================================
# 8. API TEST FLOW
# =============================================================================

class TestAPITestFlow:
    """Golden path: http_request → validate_schema → report."""

    def test_api_test_flow_completes(self, comparator, agent_trajectory):
        """API test must complete all 3 steps with non-empty answer."""
        comp = comparator("api_test")
        agent = agent_trajectory("api_test", variant="perfect")

        assert agent.final_answer, "Agent must produce a final answer"
        assert comp.task_completion_score(agent) == 1.0
        assert comp.tool_accuracy(agent) == 1.0


# =============================================================================
# 9. PERFORMANCE TEST FLOW
# =============================================================================

class TestPerformanceTestFlow:
    """Golden path: run perf suite → get baseline → compare."""

    def test_performance_flow_comparison_metrics(self, comparator, agent_trajectory):
        """Performance flow must produce comparison metrics."""
        comp = comparator("performance_test")
        agent = agent_trajectory("performance_test", variant="perfect")

        report = comp.detailed_report(agent)
        assert report["overall_score"] >= OVERALL_SCORE_THRESHOLD
        assert report["tool_error_rate"] == 0.0
        assert "compare" in agent.final_answer.lower() or "improv" in agent.final_answer.lower()


# =============================================================================
# 10. CI/CD INTEGRATION FLOW
# =============================================================================

class TestCICDIntegrationFlow:
    """Golden path: receive trigger → run smoke → gate deployment."""

    def test_ci_cd_flow_gates_deployment(self, comparator, agent_trajectory):
        """CI/CD flow must complete gating decision."""
        comp = comparator("ci_cd_integration")
        agent = agent_trajectory("ci_cd_integration", variant="perfect")

        gate_calls = [tc for tc in agent.tool_calls if tc.tool_name == "gate_deployment"]
        assert len(gate_calls) == 1, "Must have exactly one gate_deployment call"
        assert comp.task_completion_score(agent) == 1.0
        assert comp.overall_score(agent) >= OVERALL_SCORE_THRESHOLD


# =============================================================================
# BONUS: Degrade testing — verify metrics detect bad trajectories
# =============================================================================

class TestTrajectoryDegrade:
    """Verify that metrics correctly flag poor trajectories."""

    def test_wrong_tools_score_low(self, comparator, agent_trajectory):
        """Agent using wrong tools must score below threshold."""
        comp = comparator("test_execution")
        agent = agent_trajectory("test_execution", variant="wrong")

        assert comp.tool_accuracy(agent) < TOOL_ACCURACY_THRESHOLD
        assert comp.overall_score(agent) < OVERALL_SCORE_THRESHOLD

    def test_empty_trajectory_scores_zero(self, comparator):
        """Empty trajectory must score zero on all metrics."""
        comp = comparator("test_execution")
        empty = Trajectory(task="nothing", tool_calls=[], final_answer="")

        assert comp.tool_accuracy(empty) == 0.0
        assert comp.task_completion_score(empty) == 0.0
        assert comp.overall_score(empty) == 0.0

    def test_detailed_report_has_all_metrics(self, comparator, agent_trajectory):
        """detailed_report must return all expected keys."""
        comp = comparator("test_execution")
        agent = agent_trajectory("test_execution", variant="perfect")
        report = comp.detailed_report(agent)

        expected_keys = {
            "tool_accuracy", "tool_error_rate", "task_completion",
            "tool_order_fidelity", "overall_score",
            "agent_tool_count", "agent_error_count", "agent_success_rate",
        }
        assert set(report.keys()) == expected_keys
