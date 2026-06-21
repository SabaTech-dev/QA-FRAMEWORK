"""
Tests for SemanticFlow value_objects.

RED phase: estos tests definen el contrato de los value objects antes
de que exista la implementacion. Deben fallar primero.
"""

import pytest

from src.domain.semantic_flow.value_objects import (
    NodeType,
    WorkflowStatus,
    NodeStatus,
    SemanticMatch,
    WorkflowId,
    NodeId,
    EdgeId,
)


class TestNodeType:
    """NodeType enum contract."""

    def test_has_action_type(self):
        assert NodeType.ACTION == "action"

    def test_has_decision_type(self):
        assert NodeType.DECISION == "decision"

    def test_has_assertion_type(self):
        assert NodeType.ASSERTION == "assertion"

    def test_has_semantic_branch_type(self):
        assert NodeType.SEMANTIC_BRANCH == "semantic_branch"

    def test_has_start_type(self):
        assert NodeType.START == "start"

    def test_has_end_type(self):
        assert NodeType.END == "end"

    def test_is_string_enum(self):
        assert NodeType("action") is NodeType.ACTION
        assert isinstance(NodeType.ACTION.value, str)


class TestWorkflowStatus:
    """WorkflowStatus enum contract."""

    def test_pending_default(self):
        assert WorkflowStatus.PENDING == "pending"

    def test_running(self):
        assert WorkflowStatus.RUNNING == "running"

    def test_completed(self):
        assert WorkflowStatus.COMPLETED == "completed"

    def test_failed(self):
        assert WorkflowStatus.FAILED == "failed"

    def test_cancelled(self):
        assert WorkflowStatus.CANCELLED == "cancelled"

    def test_is_terminal(self):
        assert WorkflowStatus.COMPLETED.is_terminal is True
        assert WorkflowStatus.FAILED.is_terminal is True
        assert WorkflowStatus.CANCELLED.is_terminal is True
        assert WorkflowStatus.PENDING.is_terminal is False
        assert WorkflowStatus.RUNNING.is_terminal is False


class TestNodeStatus:
    """NodeStatus enum contract."""

    def test_pending(self):
        assert NodeStatus.PENDING == "pending"

    def test_running(self):
        assert NodeStatus.RUNNING == "running"

    def test_passed(self):
        assert NodeStatus.PASSED == "passed"

    def test_failed(self):
        assert NodeStatus.FAILED == "failed"

    def test_skipped(self):
        assert NodeStatus.SKIPPED == "skipped"

    def test_is_terminal(self):
        assert NodeStatus.PASSED.is_terminal is True
        assert NodeStatus.FAILED.is_terminal is True
        assert NodeStatus.SKIPPED.is_terminal is True
        assert NodeStatus.PENDING.is_terminal is False

    def test_is_success(self):
        assert NodeStatus.PASSED.is_success is True
        assert NodeStatus.FAILED.is_success is False
        assert NodeStatus.SKIPPED.is_success is False


class TestSemanticMatch:
    """SemanticMatch frozen dataclass."""

    def test_is_frozen(self):
        match = SemanticMatch(
            query="login error",
            candidate="authentication failure",
            score=0.85,
            threshold=0.7,
        )
        with pytest.raises(Exception):
            match.score = 0.5  # type: ignore[misc]

    def test_is_match_true_when_score_above_threshold(self):
        match = SemanticMatch(query="q", candidate="c", score=0.9, threshold=0.7)
        assert match.is_match is True

    def test_is_match_false_when_score_below_threshold(self):
        match = SemanticMatch(query="q", candidate="c", score=0.5, threshold=0.7)
        assert match.is_match is False

    def test_is_match_false_when_score_equals_threshold(self):
        match = SemanticMatch(query="q", candidate="c", score=0.7, threshold=0.7)
        assert match.is_match is False  # strictly greater

    def test_confidence_margin(self):
        match = SemanticMatch(query="q", candidate="c", score=0.9, threshold=0.7)
        assert match.confidence_margin == pytest.approx(0.2)


class TestTypedIdentifiers:
    """WorkflowId, NodeId, EdgeId typed strings."""

    def test_workflow_id_creates_uuid_when_empty(self):
        wid = WorkflowId()
        assert len(str(wid)) > 0

    def test_workflow_id_preserves_value(self):
        wid = WorkflowId("wf-123")
        assert str(wid) == "wf-123"

    def test_workflow_id_from_string_classmethod(self):
        wid = WorkflowId.from_string("abc")
        assert str(wid) == "abc"

    def test_node_id_creates_uuid_when_empty(self):
        nid = NodeId()
        assert len(str(nid)) > 0

    def test_node_id_preserves_value(self):
        nid = NodeId("node-1")
        assert str(nid) == "node-1"

    def test_edge_id_creates_uuid_when_empty(self):
        eid = EdgeId()
        assert len(str(eid)) > 0

    def test_edge_id_preserves_value(self):
        eid = EdgeId("edge-1")
        assert str(eid) == "edge-1"

    def test_workflow_id_equality(self):
        a = WorkflowId("x")
        b = WorkflowId("x")
        c = WorkflowId("y")
        assert a == b
        assert a != c
