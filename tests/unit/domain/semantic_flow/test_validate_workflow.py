"""
Tests for ValidateWorkflow use case.

RED phase: define el contrato de validacion de workflows (ciclos,
nodos huerfanos, ausencia de START/END, edges rotos).
"""


from src.domain.semantic_flow.entities import Node, Edge, Workflow
from src.domain.semantic_flow.value_objects import NodeType, NodeId, EdgeId
from src.domain.semantic_flow.use_cases.validate_workflow import (
    ValidateWorkflow,
    ValidateWorkflowInput,
    ValidateWorkflowOutput,
    ValidationIssue,
    ValidationSeverity,
)


def _node(nid: str, ntype: NodeType, label: str = "") -> Node:
    return Node(id=NodeId(nid), type=ntype, label=label or nid)


def _edge(src: str, tgt: str, eid: str = "") -> Edge:
    return Edge(id=EdgeId(eid or f"{src}-{tgt}"), source=NodeId(src), target=NodeId(tgt))


class TestValidationIssue:
    """ValidationIssue value object."""

    def test_error_severity(self):
        issue = ValidationIssue.error("node-x", "Missing node")
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.node_id == "node-x"
        assert issue.message == "Missing node"

    def test_warning_severity(self):
        issue = ValidationIssue.warning("node-x", "Suggestion")
        assert issue.severity == ValidationSeverity.WARNING

    def test_is_error(self):
        assert ValidationIssue.error("n", "m").is_error is True
        assert ValidationIssue.warning("n", "m").is_error is False


class TestValidateWorkflow:
    """ValidateWorkflow use case."""

    def test_valid_linear_workflow_passes(self):
        wf = Workflow(
            name="valid",
            nodes={
                "start": _node("start", NodeType.START),
                "action": _node("action", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "action"),
                _edge("action", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is True
        assert len([i for i in result.issues if i.is_error]) == 0

    def test_missing_start_node_is_error(self):
        wf = Workflow(
            name="no-start",
            nodes={"end": _node("end", NodeType.END)},
            edges=[],
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False
        assert any("start" in i.message.lower() for i in result.issues if i.is_error)

    def test_missing_end_node_is_error(self):
        wf = Workflow(
            name="no-end",
            nodes={"start": _node("start", NodeType.START)},
            edges=[],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False
        assert any("end" in i.message.lower() for i in result.issues if i.is_error)

    def test_cycle_is_detected(self):
        """A -> B -> A forms a cycle."""
        wf = Workflow(
            name="cycle",
            nodes={
                "start": _node("start", NodeType.START),
                "a": _node("a", NodeType.ACTION),
                "b": _node("b", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "a"),
                _edge("a", "b"),
                _edge("b", "a"),  # cycle
                _edge("b", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False
        assert any("cycle" in i.message.lower() for i in result.issues if i.is_error)

    def test_orphan_node_is_warning(self):
        """Node not reachable from start."""
        wf = Workflow(
            name="orphan",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
                "orphan": _node("orphan", NodeType.ACTION),
            },
            edges=[_edge("start", "end")],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        # orphan is a warning, not blocking
        assert any("orphan" in i.message.lower() for i in result.issues)
        assert any(i.node_id == "orphan" for i in result.issues)

    def test_edge_to_unknown_target_is_error(self):
        wf = Workflow(
            name="broken-edge",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "ghost")],  # ghost does not exist
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False
        assert any(
            "ghost" in i.message.lower() or "ghost" in (i.node_id or "")
            for i in result.issues
            if i.is_error
        )

    def test_edge_from_unknown_source_is_error(self):
        wf = Workflow(
            name="broken-edge-src",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("ghost", "end")],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False

    def test_empty_workflow_is_invalid(self):
        wf = Workflow(name="empty")
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False

    def test_output_contains_summary(self):
        wf = Workflow(
            name="valid",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "end")],
            start_node_id=NodeId("start"),
        )
        out = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert isinstance(out, ValidateWorkflowOutput)
        assert out.error_count == 0
        assert out.warning_count == 0
        assert isinstance(out.issues, list)

    def test_self_loop_is_cycle(self):
        wf = Workflow(
            name="self-loop",
            nodes={
                "start": _node("start", NodeType.START),
                "a": _node("a", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "a"),
                _edge("a", "a"),  # self-loop
                _edge("a", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        result = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
        assert result.is_valid is False
