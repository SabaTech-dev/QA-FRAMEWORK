"""
Tests for SemanticFlow entities.

RED phase: define el contrato de Node, Edge, Workflow, ExecutionContext,
NodeResult, WorkflowResult antes de implementarlos.
"""

from datetime import datetime


from src.domain.semantic_flow.entities import (
    Node,
    Edge,
    Workflow,
    ExecutionContext,
    NodeResult,
    WorkflowResult,
)
from src.domain.semantic_flow.value_objects import (
    NodeType,
    WorkflowStatus,
    NodeStatus,
    NodeId,
    EdgeId,
    WorkflowId,
)


class TestNode:
    """Node entity."""

    def test_create_action_node_with_defaults(self):
        node = Node(type=NodeType.ACTION, label="Click login")
        assert node.type == NodeType.ACTION
        assert node.label == "Click login"
        assert node.id is not None
        assert node.inputs == {}
        assert node.metadata == {}

    def test_create_with_explicit_id(self):
        nid = NodeId("custom-id")
        node = Node(id=nid, type=NodeType.START, label="start")
        assert str(node.id) == "custom-id"

    def test_is_terminal_property(self):
        assert Node(type=NodeType.END, label="end").is_terminal is True
        assert Node(type=NodeType.START, label="start").is_terminal is False

    def test_is_semantic_property(self):
        assert Node(type=NodeType.SEMANTIC_BRANCH, label="sb").is_semantic is True
        assert Node(type=NodeType.ACTION, label="a").is_semantic is False

    def test_to_dict_serialization(self):
        node = Node(
            type=NodeType.ACTION,
            label="Click button",
            inputs={"selector": "#submit"},
        )
        d = node.to_dict()
        assert d["type"] == "action"
        assert d["label"] == "Click button"
        assert d["inputs"]["selector"] == "#submit"
        assert "id" in d


class TestEdge:
    """Edge entity."""

    def test_create_unconditional_edge(self):
        edge = Edge(
            source=NodeId("a"),
            target=NodeId("b"),
        )
        assert str(edge.source) == "a"
        assert str(edge.target) == "b"
        assert edge.condition is None
        assert edge.priority == 0

    def test_create_conditional_edge_with_priority(self):
        edge = Edge(
            source=NodeId("a"),
            target=NodeId("b"),
            condition="success",
            priority=10,
        )
        assert edge.condition == "success"
        assert edge.priority == 10

    def test_is_conditional(self):
        conditional = Edge(source=NodeId("a"), target=NodeId("b"), condition="x")
        unconditional = Edge(source=NodeId("a"), target=NodeId("b"))
        assert conditional.is_conditional is True
        assert unconditional.is_conditional is False

    def test_to_dict_serialization(self):
        edge = Edge(
            id=EdgeId("e1"),
            source=NodeId("a"),
            target=NodeId("b"),
            condition="ok",
            priority=5,
        )
        d = edge.to_dict()
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["condition"] == "ok"
        assert d["priority"] == 5


class TestWorkflow:
    """Workflow aggregate root."""

    def _make_simple_workflow(self) -> Workflow:
        """START -> ACTION -> END."""
        start = Node(id=NodeId("start"), type=NodeType.START, label="start")
        action = Node(id=NodeId("action"), type=NodeType.ACTION, label="do")
        end = Node(id=NodeId("end"), type=NodeType.END, label="end")
        wf = Workflow(
            name="simple",
            nodes={"start": start, "action": action, "end": end},
            edges=[
                Edge(id=EdgeId("e1"), source=NodeId("start"), target=NodeId("action")),
                Edge(id=EdgeId("e2"), source=NodeId("action"), target=NodeId("end")),
            ],
            start_node_id=NodeId("start"),
        )
        return wf

    def test_create_workflow_with_defaults(self):
        wf = Workflow(name="empty")
        assert wf.name == "empty"
        assert wf.nodes == {}
        assert wf.edges == []
        assert wf.status == WorkflowStatus.PENDING
        assert wf.tenant_id is None

    def test_get_node_by_id(self):
        wf = self._make_simple_workflow()
        node = wf.get_node("action")
        assert node is not None
        assert node.label == "do"

    def test_get_node_returns_none_for_unknown(self):
        wf = self._make_simple_workflow()
        assert wf.get_node("nope") is None

    def test_node_count(self):
        wf = self._make_simple_workflow()
        assert wf.node_count == 3

    def test_edge_count(self):
        wf = self._make_simple_workflow()
        assert wf.edge_count == 2

    def test_end_nodes_property(self):
        wf = self._make_simple_workflow()
        end_nodes = wf.end_nodes
        assert len(end_nodes) == 1
        assert end_nodes[0].type == NodeType.END

    def test_outgoing_edges_for_node(self):
        wf = self._make_simple_workflow()
        outgoing = wf.outgoing_edges("start")
        assert len(outgoing) == 1
        assert str(outgoing[0].target) == "action"

    def test_outgoing_edges_sorted_by_priority(self):
        start = Node(id=NodeId("s"), type=NodeType.START, label="s")
        a = Node(id=NodeId("a"), type=NodeType.ACTION, label="a")
        b = Node(id=NodeId("b"), type=NodeType.ACTION, label="b")
        wf = Workflow(
            name="priority",
            nodes={"s": start, "a": a, "b": b},
            edges=[
                Edge(id=EdgeId("e1"), source=NodeId("s"), target=NodeId("a"), priority=1),
                Edge(id=EdgeId("e2"), source=NodeId("s"), target=NodeId("b"), priority=10),
            ],
            start_node_id=NodeId("s"),
        )
        out = wf.outgoing_edges("s")
        assert str(out[0].target) == "b"  # higher priority first

    def test_has_start_node(self):
        wf = self._make_simple_workflow()
        assert wf.has_start_node is True

    def test_no_start_node(self):
        wf = Workflow(name="no-start")
        assert wf.has_start_node is False

    def test_with_status_returns_new_instance(self):
        wf = self._make_simple_workflow()
        running = wf.with_status(WorkflowStatus.RUNNING)
        assert wf.status == WorkflowStatus.PENDING  # immutable
        assert running.status == WorkflowStatus.RUNNING
        assert running is not wf

    def test_to_dict_serialization(self):
        wf = self._make_simple_workflow()
        d = wf.to_dict()
        assert d["name"] == "simple"
        assert d["node_count"] == 3
        assert d["edge_count"] == 2
        assert d["status"] == "pending"
        assert "nodes" in d
        assert "edges" in d


class TestNodeResult:
    """NodeResult entity."""

    def test_passed_result(self):
        r = NodeResult.passed(
            node_id=NodeId("n1"),
            output={"value": 42},
            score=0.95,
        )
        assert r.node_id == NodeId("n1")
        assert r.status == NodeStatus.PASSED
        assert r.output == {"value": 42}
        assert r.score == 0.95
        assert r.error is None
        assert r.duration_ms >= 0

    def test_failed_result(self):
        r = NodeResult.failed(
            node_id=NodeId("n1"),
            error="boom",
        )
        assert r.status == NodeStatus.FAILED
        assert r.error == "boom"
        assert r.output == {}

    def test_skipped_result(self):
        r = NodeResult.skipped(node_id=NodeId("n1"))
        assert r.status == NodeStatus.SKIPPED

    def test_is_success(self):
        assert NodeResult.passed(node_id=NodeId("n1")).is_success is True
        assert NodeResult.failed(node_id=NodeId("n1"), error="x").is_success is False

    def test_to_dict(self):
        r = NodeResult.passed(node_id=NodeId("n1"), output={"k": "v"})
        d = r.to_dict()
        assert d["node_id"] == "n1"
        assert d["status"] == "passed"
        assert d["output"] == {"k": "v"}


class TestWorkflowResult:
    """WorkflowResult entity."""

    def test_create_with_defaults(self):
        r = WorkflowResult(workflow_id=WorkflowId("wf1"))
        assert str(r.workflow_id) == "wf1"
        assert r.status == WorkflowStatus.PENDING
        assert r.node_results == []
        assert r.duration_ms == 0

    def test_success_rate_empty(self):
        r = WorkflowResult(workflow_id=WorkflowId("wf1"))
        assert r.success_rate == 0.0

    def test_success_rate_all_passed(self):
        r = WorkflowResult(
            workflow_id=WorkflowId("wf1"),
            node_results=[
                NodeResult.passed(node_id=NodeId("a")),
                NodeResult.passed(node_id=NodeId("b")),
            ],
        )
        assert r.success_rate == 1.0

    def test_success_rate_half(self):
        r = WorkflowResult(
            workflow_id=WorkflowId("wf1"),
            node_results=[
                NodeResult.passed(node_id=NodeId("a")),
                NodeResult.failed(node_id=NodeId("b"), error="x"),
            ],
        )
        assert r.success_rate == 0.5

    def test_passed_count(self):
        r = WorkflowResult(
            workflow_id=WorkflowId("wf1"),
            node_results=[
                NodeResult.passed(node_id=NodeId("a")),
                NodeResult.failed(node_id=NodeId("b"), error="x"),
                NodeResult.skipped(node_id=NodeId("c")),
            ],
        )
        assert r.passed_count == 1
        assert r.failed_count == 1
        assert r.skipped_count == 1

    def test_is_terminal(self):
        assert (
            WorkflowResult(
                workflow_id=WorkflowId("wf1"), status=WorkflowStatus.COMPLETED
            ).is_terminal
            is True
        )
        assert (
            WorkflowResult(workflow_id=WorkflowId("wf1"), status=WorkflowStatus.RUNNING).is_terminal
            is False
        )

    def test_to_dict(self):
        r = WorkflowResult(
            workflow_id=WorkflowId("wf1"),
            status=WorkflowStatus.COMPLETED,
            node_results=[NodeResult.passed(node_id=NodeId("a"))],
            duration_ms=150,
        )
        d = r.to_dict()
        assert d["workflow_id"] == "wf1"
        assert d["status"] == "completed"
        assert d["duration_ms"] == 150
        assert len(d["node_results"]) == 1


class TestExecutionContext:
    """ExecutionContext entity."""

    def test_create_with_defaults(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        assert str(ctx.workflow_id) == "wf1"
        assert ctx.variables == {}
        assert ctx.history == []
        assert ctx.current_node_id is None
        assert isinstance(ctx.started_at, datetime)

    def test_set_variable(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        ctx.set_variable("user", "alice")
        assert ctx.get_variable("user") == "alice"

    def test_get_variable_default(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        assert ctx.get_variable("missing", "fallback") == "fallback"

    def test_record_result_appends_to_history(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        result = NodeResult.passed(node_id=NodeId("n1"))
        ctx.record_result(result)
        assert len(ctx.history) == 1
        assert ctx.history[0] == result

    def test_last_result(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        r1 = NodeResult.passed(node_id=NodeId("n1"))
        r2 = NodeResult.passed(node_id=NodeId("n2"))
        ctx.record_result(r1)
        ctx.record_result(r2)
        assert ctx.last_result == r2

    def test_last_result_empty(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        assert ctx.last_result is None

    def test_total_duration_ms(self):
        ctx = ExecutionContext(workflow_id=WorkflowId("wf1"))
        ctx.record_result(NodeResult.passed(node_id=NodeId("n1"), duration_ms=100))
        ctx.record_result(NodeResult.passed(node_id=NodeId("n2"), duration_ms=200))
        assert ctx.total_duration_ms == 300
