"""
Tests for ExecuteWorkflow use case.

RED phase: define el contrato de ejecucion de workflows, caso lineal,
caso con decision binaria, caso con fallo, caso vacio.
"""

from src.domain.semantic_flow.entities import Node, Edge, Workflow, NodeResult
from src.domain.semantic_flow.interfaces import (
    NodeExecutor,
)
from src.domain.semantic_flow.use_cases.execute_workflow import (
    ExecuteWorkflow,
    ExecuteWorkflowInput,
)
from src.domain.semantic_flow.value_objects import (
    NodeType,
    NodeId,
    EdgeId,
    WorkflowId,
    WorkflowStatus,
)


def _node(nid: str, ntype: NodeType, label: str = "") -> Node:
    return Node(id=NodeId(nid), type=ntype, label=label or nid)


def _edge(src: str, tgt: str, condition: str = "", priority: int = 0, eid: str = "") -> Edge:
    return Edge(
        id=EdgeId(eid or f"{src}-{tgt}"),
        source=NodeId(src),
        target=NodeId(tgt),
        condition=condition or None,
        priority=priority,
    )


class _StubNodeExecutor(NodeExecutor):
    """Executor stub that runs a dict of {node_id: callable}."""

    def __init__(self, handlers=None):
        self.handlers = handlers or {}
        self.calls = []

    def execute(self, node, context):
        self.calls.append(str(node.id))
        handler = self.handlers.get(str(node.id))
        if handler is None:
            return NodeResult.passed(node_id=node.id)
        return handler(node, context)


class TestExecuteWorkflowLinear:
    """Linear workflow execution START -> ACTION -> END."""

    def test_linear_execution_visits_all_nodes(self):
        wf = Workflow(
            id=WorkflowId("wf-1"),
            name="linear",
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
        executor = _StubNodeExecutor()
        use_case = ExecuteWorkflow(node_executor=executor)
        out = use_case.execute(ExecuteWorkflowInput(workflow=wf))

        assert out.success is True
        assert executor.calls == ["start", "action", "end"]
        assert out.result.status == WorkflowStatus.COMPLETED
        assert out.result.passed_count == 3

    def test_execution_returns_workflow_result(self):
        wf = Workflow(
            name="minimal",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "end")],
            start_node_id=NodeId("start"),
        )
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf))
        assert out.result is not None
        assert out.result.workflow_id == wf.id

    def test_execution_records_duration(self):
        wf = Workflow(
            name="minimal",
            nodes={
                "start": _node("start", NodeType.START),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "end")],
            start_node_id=NodeId("start"),
        )
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf))
        assert out.result.duration_ms >= 0


class TestExecuteWorkflowDecision:
    """DECISION node routes based on result status."""

    def test_decision_routes_to_passed_branch(self):
        wf = Workflow(
            name="decision",
            nodes={
                "start": _node("start", NodeType.START),
                "check": _node("check", NodeType.DECISION, "check status"),
                "ok": _node("ok", NodeType.ACTION),
                "fail": _node("fail", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "check"),
                _edge("check", "ok", condition="passed"),
                _edge("check", "fail", condition="failed"),
                _edge("ok", "end"),
                _edge("fail", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        # check always passes
        executor = _StubNodeExecutor(
            {
                "check": lambda n, c: NodeResult.passed(node_id=n.id),
            }
        )
        out = ExecuteWorkflow(node_executor=executor).execute(ExecuteWorkflowInput(workflow=wf))
        assert out.success is True
        assert "fail" not in executor.calls
        assert "ok" in executor.calls

    def test_decision_routes_to_failed_branch(self):
        wf = Workflow(
            name="decision-fail",
            nodes={
                "start": _node("start", NodeType.START),
                "check": _node("check", NodeType.DECISION),
                "ok": _node("ok", NodeType.ACTION),
                "fail": _node("fail", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "check"),
                _edge("check", "ok", condition="passed"),
                _edge("check", "fail", condition="failed"),
                _edge("ok", "end"),
                _edge("fail", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        executor = _StubNodeExecutor(
            {
                "check": lambda n, c: NodeResult.failed(node_id=n.id, error="nope"),
            }
        )
        out = ExecuteWorkflow(node_executor=executor).execute(ExecuteWorkflowInput(workflow=wf))
        # DECISION failure is routing info, not workflow failure
        assert out.success is True
        assert "fail" in executor.calls
        assert "ok" not in executor.calls

    def test_decision_no_matching_condition_skips_branch(self):
        """DECISION with no matching edge condition: skip remaining and end."""
        wf = Workflow(
            name="decision-no-match",
            nodes={
                "start": _node("start", NodeType.START),
                "check": _node("check", NodeType.DECISION),
                "ok": _node("ok", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "check"),
                _edge("check", "ok", condition="passed"),
                # no edge from check to end with condition="failed"
                _edge("ok", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        executor = _StubNodeExecutor(
            {
                "check": lambda n, c: NodeResult.failed(node_id=n.id, error="x"),
            }
        )
        out = ExecuteWorkflow(node_executor=executor).execute(ExecuteWorkflowInput(workflow=wf))
        # No matching branch: workflow completes but no end node visited
        assert out.result.status == WorkflowStatus.COMPLETED


class TestExecuteWorkflowFailure:
    """Action node failure stops workflow."""

    def test_action_failure_marks_workflow_failed(self):
        wf = Workflow(
            name="with-failure",
            nodes={
                "start": _node("start", NodeType.START),
                "fail": _node("fail", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "fail"),
                _edge("fail", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        executor = _StubNodeExecutor(
            {
                "fail": lambda n, c: NodeResult.failed(node_id=n.id, error="boom"),
            }
        )
        out = ExecuteWorkflow(node_executor=executor).execute(ExecuteWorkflowInput(workflow=wf))
        assert out.success is False
        assert out.result.status == WorkflowStatus.FAILED
        assert "end" not in executor.calls


class TestExecuteWorkflowEdgeCases:
    """Edge cases."""

    def test_empty_workflow_fails_gracefully(self):
        wf = Workflow(name="empty")
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf))
        assert out.success is False
        assert out.result.status == WorkflowStatus.FAILED
        assert out.error_message is not None

    def test_no_start_node_fails_gracefully(self):
        wf = Workflow(
            name="no-start",
            nodes={"end": _node("end", NodeType.END)},
            edges=[],
        )
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf))
        assert out.success is False

    def test_handles_exception_in_executor(self):
        wf = Workflow(
            name="exception",
            nodes={
                "start": _node("start", NodeType.START),
                "boom": _node("boom", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "boom"), _edge("boom", "end")],
            start_node_id=NodeId("start"),
        )

        class _CrashingExecutor(NodeExecutor):
            def execute(self, node, context):
                raise RuntimeError("crashed")

        out = ExecuteWorkflow(node_executor=_CrashingExecutor()).execute(
            ExecuteWorkflowInput(workflow=wf)
        )
        assert out.success is False
        assert "crashed" in (out.error_message or "")

    def test_context_accumulates_history(self):
        wf = Workflow(
            name="history",
            nodes={
                "start": _node("start", NodeType.START),
                "a": _node("a", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[_edge("start", "a"), _edge("a", "end")],
            start_node_id=NodeId("start"),
        )
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf))
        assert len(out.result.node_results) == 3
        ids = [str(r.node_id) for r in out.result.node_results]
        assert ids == ["start", "a", "end"]


class TestExecuteWorkflowMaxSteps:
    """Infinite loop protection via max_steps."""

    def test_max_steps_prevents_infinite_loop(self):
        """A -> B -> A would loop forever without max_steps."""
        wf = Workflow(
            name="loop",
            nodes={
                "start": _node("start", NodeType.START),
                "a": _node("a", NodeType.ACTION),
                "b": _node("b", NodeType.ACTION),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "a"),
                _edge("a", "b"),
                _edge("b", "a"),  # would loop
            ],
            start_node_id=NodeId("start"),
        )
        out = ExecuteWorkflow().execute(ExecuteWorkflowInput(workflow=wf, max_steps=10))
        # Should terminate (not crash); status reflects abnormal end
        assert out.result.status in (WorkflowStatus.FAILED, WorkflowStatus.COMPLETED)
        assert len(out.result.node_results) <= 10
