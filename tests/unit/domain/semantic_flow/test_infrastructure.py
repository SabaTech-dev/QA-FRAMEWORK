"""
Tests para los executors concretos de infraestructura.

Cubre ActionNodeExecutor, AssertionNodeExecutor, CompositeNodeExecutor
y el InMemoryWorkflowRepository.
"""


from src.domain.semantic_flow.entities import (
    ExecutionContext,
    Node,
    Workflow,
    NodeResult,
)
from src.infrastructure.semantic_flow import (
    ActionNodeExecutor,
    AssertionNodeExecutor,
    CompositeNodeExecutor,
    InMemoryWorkflowRepository,
)
from src.domain.semantic_flow.value_objects import (
    NodeId,
    NodeType,
    WorkflowId,
)


class TestActionNodeExecutor:
    """ActionNodeExecutor."""

    def test_no_handler_returns_passed(self):
        executor = ActionNodeExecutor()
        node = Node(id=NodeId("n1"), type=NodeType.ACTION, label="n1")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "passed"
        assert str(result.node_id) == "n1"

    def test_registered_handler_is_called(self):
        calls = []

        def handler(n, c):
            calls.append(str(n.id))
            return NodeResult.passed(node_id=n.id, output={"ok": True})

        executor = ActionNodeExecutor({"n1": handler})
        node = Node(id=NodeId("n1"), type=NodeType.ACTION, label="n1")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert calls == ["n1"]
        assert result.output == {"ok": True}

    def test_register_adds_handler(self):
        executor = ActionNodeExecutor()
        executor.register("xyz", lambda n, c: NodeResult.failed(node_id=n.id, error="x"))
        node = Node(id=NodeId("xyz"), type=NodeType.ACTION, label="xyz")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "failed"


class TestAssertionNodeExecutor:
    """AssertionNodeExecutor."""

    def test_no_assertion_returns_passed(self):
        executor = AssertionNodeExecutor()
        node = Node(id=NodeId("a1"), type=NodeType.ASSERTION, label="a1")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "passed"

    def test_passing_assertion(self):
        executor = AssertionNodeExecutor()
        node = Node(
            id=NodeId("a1"),
            type=NodeType.ASSERTION,
            label="a1",
            inputs={"assert": lambda c: True},
        )
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "passed"
        assert result.output == {"assertion": True}

    def test_failing_assertion(self):
        executor = AssertionNodeExecutor()
        node = Node(
            id=NodeId("a1"),
            type=NodeType.ASSERTION,
            label="a1",
            inputs={"assert": lambda c: False},
        )
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "failed"
        assert "False" in (result.error or "")

    def test_assertion_raising_exception(self):
        executor = AssertionNodeExecutor()

        def boom(c):
            raise ValueError("kaboom")

        node = Node(
            id=NodeId("a1"),
            type=NodeType.ASSERTION,
            label="a1",
            inputs={"assert": boom},
        )
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = executor.execute(node, ctx)
        assert result.status.value == "failed"
        assert "kaboom" in (result.error or "")


class TestCompositeNodeExecutor:
    """CompositeNodeExecutor."""

    def test_unregistered_type_defaults_to_passed(self):
        composite = CompositeNodeExecutor()
        node = Node(id=NodeId("a"), type=NodeType.ACTION, label="a")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = composite.execute(node, ctx)
        assert result.status.value == "passed"

    def test_dispatches_by_type(self):
        composite = CompositeNodeExecutor()
        action_exec = ActionNodeExecutor(
            {"a1": lambda n, c: NodeResult.passed(node_id=n.id, output={"via": "action"})}
        )
        composite.register(NodeType.ACTION, action_exec)

        node = Node(id=NodeId("a1"), type=NodeType.ACTION, label="a1")
        ctx = ExecutionContext(workflow_id=WorkflowId("wf"))
        result = composite.execute(node, ctx)
        assert result.output == {"via": "action"}

    def test_register_returns_self_for_chaining(self):
        composite = CompositeNodeExecutor()
        ret = composite.register(NodeType.ASSERTION, AssertionNodeExecutor())
        assert ret is composite


class TestInMemoryWorkflowRepository:
    """InMemoryWorkflowRepository."""

    def _make_wf(self, name="wf", tenant=None):
        return Workflow(name=name, tenant_id=tenant)

    def test_save_and_get_by_id(self):
        repo = InMemoryWorkflowRepository()
        wf = self._make_wf()
        repo.save(wf)
        fetched = repo.get_by_id(wf.id)
        assert fetched is wf

    def test_get_by_id_returns_none_for_unknown(self):
        repo = InMemoryWorkflowRepository()
        assert repo.get_by_id(WorkflowId("nope")) is None

    def test_get_by_tenant_filters_correctly(self):
        repo = InMemoryWorkflowRepository()
        wf_a = self._make_wf("a", tenant="t1")
        wf_b = self._make_wf("b", tenant="t1")
        wf_c = self._make_wf("c", tenant="t2")
        repo.save(wf_a)
        repo.save(wf_b)
        repo.save(wf_c)

        t1_results = repo.get_by_tenant("t1")
        assert len(t1_results) == 2
        t2_results = repo.get_by_tenant("t2")
        assert len(t2_results) == 1

    def test_get_by_tenant_respects_limit(self):
        repo = InMemoryWorkflowRepository()
        for i in range(5):
            repo.save(self._make_wf(f"wf-{i}", tenant="t"))
        results = repo.get_by_tenant("t", limit=2)
        assert len(results) == 2

    def test_get_by_tenant_empty_for_unknown(self):
        repo = InMemoryWorkflowRepository()
        assert repo.get_by_tenant("ghost") == []

    def test_save_overwrites_existing(self):
        from src.domain.semantic_flow.value_objects import WorkflowStatus

        repo = InMemoryWorkflowRepository()
        wf = self._make_wf("orig")
        repo.save(wf)
        updated = wf.with_status(WorkflowStatus.RUNNING)
        repo.save(updated)
        fetched = repo.get_by_id(wf.id)
        assert fetched.status == WorkflowStatus.RUNNING
