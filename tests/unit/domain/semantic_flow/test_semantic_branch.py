"""
Tests for SemanticBranch node + SemanticProcessor integration.

RED phase: define el contrato de ramificacion semantica.
"""

import pytest

from src.domain.semantic_flow.entities import Node, Edge, Workflow, NodeResult
from src.domain.semantic_flow.use_cases.execute_workflow import (
    ExecuteWorkflow,
    ExecuteWorkflowInput,
)
from src.domain.semantic_flow.value_objects import (
    NodeType,
    NodeId,
    EdgeId,
    SemanticMatch,
)


def _node(nid: str, ntype: NodeType, label: str = "") -> Node:
    return Node(id=NodeId(nid), type=ntype, label=label or nid)


def _edge(src: str, tgt: str, condition: str = "", eid: str = "") -> Edge:
    return Edge(
        id=EdgeId(eid or f"{src}-{tgt}"),
        source=NodeId(src),
        target=NodeId(tgt),
        condition=condition or None,
    )


class _FakeSemanticProcessor:
    """SemanticProcessor stub returning canned matches."""

    def __init__(self, scores: dict):
        self.scores = scores  # {candidate_label: score}
        self.calls = []

    def embed(self, text):
        return [0.0]  # not used

    def similarity(self, a, b):
        return 0.0

    def best_match(self, query, candidates, threshold=0.5):
        self.calls.append((query, candidates, threshold))
        best = None
        best_score = -1.0
        for c in candidates:
            score = self.scores.get(c, 0.0)
            if score > best_score:
                best_score = score
                best = c
        return SemanticMatch(
            query=query,
            candidate=best or "",
            score=best_score,
            threshold=threshold,
        )


class TestSemanticBranch:
    """SEMANTIC_BRANCH node routes by similarity."""

    def test_routes_to_best_match(self):
        wf = Workflow(
            name="semantic",
            nodes={
                "start": _node("start", NodeType.START),
                "branch": _node("branch", NodeType.SEMANTIC_BRANCH, "classify error"),
                "auth": _node("auth", NodeType.ACTION, "authentication failure"),
                "network": _node("network", NodeType.ACTION, "network timeout"),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "branch"),
                _edge("branch", "auth", condition="authentication failure"),
                _edge("branch", "network", condition="network timeout"),
                _edge("auth", "end"),
                _edge("network", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        # auth gets higher score
        proc = _FakeSemanticProcessor(
            {
                "authentication failure": 0.9,
                "network timeout": 0.3,
            }
        )

        from src.domain.semantic_flow.entities import NodeResult

        class _RecordingExecutor:
            def __init__(self):
                self.visited = []

            def execute(self, node, context):
                self.visited.append(str(node.id))
                return NodeResult.passed(node_id=node.id)

        recorder = _RecordingExecutor()
        from src.domain.semantic_flow.use_cases.execute_workflow import (
            ExecuteWorkflow,
            ExecuteWorkflowInput,
        )

        use_case = ExecuteWorkflow(
            node_executor=recorder,
            semantic_processor=proc,
        )
        out = use_case.execute(ExecuteWorkflowInput(workflow=wf, branch_query="login auth error"))
        assert out.success is True
        assert "auth" in recorder.visited
        assert "network" not in recorder.visited

    def test_no_match_above_threshold_completes_without_branch(self):
        wf = Workflow(
            name="semantic-no-match",
            nodes={
                "start": _node("start", NodeType.START),
                "branch": _node("branch", NodeType.SEMANTIC_BRANCH),
                "a": _node("a", NodeType.ACTION, "alpha"),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "branch"),
                _edge("branch", "a", condition="alpha"),
                _edge("a", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        proc = _FakeSemanticProcessor({"alpha": 0.2})  # below threshold 0.5

        class _RecordingExecutor:
            def __init__(self):
                self.visited = []

            def execute(self, node, context):
                self.visited.append(str(node.id))
                return NodeResult.passed(node_id=node.id)

        recorder = _RecordingExecutor()
        use_case = ExecuteWorkflow(
            node_executor=recorder,
            semantic_processor=proc,
        )
        out = use_case.execute(ExecuteWorkflowInput(workflow=wf, branch_query="zzz"))
        assert out.result.status.value == "completed"
        assert "a" not in recorder.visited

    def test_semantic_processor_uses_query_from_input(self):
        wf = Workflow(
            name="semantic-query",
            nodes={
                "start": _node("start", NodeType.START),
                "branch": _node("branch", NodeType.SEMANTIC_BRANCH, "decide"),
                "a": _node("a", NodeType.ACTION, "apple"),
                "end": _node("end", NodeType.END),
            },
            edges=[
                _edge("start", "branch"),
                _edge("branch", "a", condition="apple"),
                _edge("a", "end"),
            ],
            start_node_id=NodeId("start"),
        )
        proc = _FakeSemanticProcessor({"apple": 0.9})

        class _PassExecutor:
            def execute(self, node, context):
                return NodeResult.passed(node_id=node.id)

        use_case = ExecuteWorkflow(
            node_executor=_PassExecutor(),
            semantic_processor=proc,
        )
        use_case.execute(ExecuteWorkflowInput(workflow=wf, branch_query="fruit please"))
        # The processor must have been called with our query
        assert len(proc.calls) == 1
        query, candidates, threshold = proc.calls[0]
        assert query == "fruit please"
        assert "apple" in candidates


class TestEmbeddingProcessor:
    """Integration test with real EmbeddingProcessor (infrastructure)."""

    def test_embedding_processor_basic_similarity(self):
        from src.infrastructure.semantic_flow.embedding_processor import (
            EmbeddingProcessor,
        )

        proc = EmbeddingProcessor()
        sim = proc.similarity("login failed", "login failed")
        assert sim == pytest.approx(1.0)

    def test_embedding_processor_orthogonal(self):
        from src.infrastructure.semantic_flow.embedding_processor import (
            EmbeddingProcessor,
        )

        proc = EmbeddingProcessor()
        # No shared words -> similarity 0
        sim = proc.similarity("aaa bbb", "ccc ddd")
        assert sim == pytest.approx(0.0)

    def test_embedding_processor_partial_overlap(self):
        from src.infrastructure.semantic_flow.embedding_processor import (
            EmbeddingProcessor,
        )

        proc = EmbeddingProcessor()
        sim = proc.similarity("login auth error", "login failure")
        assert 0.0 < sim < 1.0

    def test_best_match_returns_match_object(self):
        from src.infrastructure.semantic_flow.embedding_processor import (
            EmbeddingProcessor,
        )
        from src.domain.semantic_flow.value_objects import SemanticMatch

        proc = EmbeddingProcessor()
        # Query con tokens compartidos con "authentication failure"
        match = proc.best_match(
            query="authentication failure detected",
            candidates=["network timeout", "authentication failure"],
            threshold=0.1,
        )
        assert isinstance(match, SemanticMatch)
        assert match.candidate == "authentication failure"
        assert match.score > 0.1
