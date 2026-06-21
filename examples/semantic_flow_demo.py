"""
Demo de SemanticFlow Testing.

Ejecutar con:
    python examples/semantic_flow_demo.py

Demuestra:
1. Construccion de un workflow semantico.
2. Validacion estructural.
3. Ejecucion con branching semantico.
4. Reporte de resultados.
"""

from src.domain.semantic_flow import (
    Edge,
    EdgeId,
    ExecuteWorkflow,
    ExecuteWorkflowInput,
    Node,
    NodeId,
    NodeType,
    ValidateWorkflow,
    ValidateWorkflowInput,
    Workflow,
    WorkflowStatus,
)
from src.infrastructure.semantic_flow import EmbeddingProcessor


def build_classifier_workflow() -> Workflow:
    """Workflow que clasifica errores de login por similitud semantica."""
    return Workflow(
        name="error_classifier",
        tenant_id="demo-tenant",
        nodes={
            "start": Node(id=NodeId("start"), type=NodeType.START, label="Inicio"),
            "classify": Node(
                id=NodeId("classify"),
                type=NodeType.SEMANTIC_BRANCH,
                label="Clasificar tipo de error",
            ),
            "auth_handler": Node(
                id=NodeId("auth_handler"),
                type=NodeType.ACTION,
                label="authentication failure",
            ),
            "network_handler": Node(
                id=NodeId("network_handler"),
                type=NodeType.ACTION,
                label="network timeout",
            ),
            "validation_handler": Node(
                id=NodeId("validation_handler"),
                type=NodeType.ACTION,
                label="validation error invalid input",
            ),
            "end": Node(id=NodeId("end"), type=NodeType.END, label="Fin"),
        },
        edges=[
            Edge(id=EdgeId("e1"), source=NodeId("start"), target=NodeId("classify")),
            Edge(
                id=EdgeId("e2"),
                source=NodeId("classify"),
                target=NodeId("auth_handler"),
                condition="authentication failure",
                priority=10,
            ),
            Edge(
                id=EdgeId("e3"),
                source=NodeId("classify"),
                target=NodeId("network_handler"),
                condition="network timeout",
                priority=5,
            ),
            Edge(
                id=EdgeId("e4"),
                source=NodeId("classify"),
                target=NodeId("validation_handler"),
                condition="validation error invalid input",
                priority=1,
            ),
            Edge(id=EdgeId("e5"), source=NodeId("auth_handler"), target=NodeId("end")),
            Edge(id=EdgeId("e6"), source=NodeId("network_handler"), target=NodeId("end")),
            Edge(
                id=EdgeId("e7"),
                source=NodeId("validation_handler"),
                target=NodeId("end"),
            ),
        ],
        start_node_id=NodeId("start"),
    )


def run_demo() -> None:
    wf = build_classifier_workflow()

    print("=" * 70)
    print("SemanticFlow Testing - Demo")
    print("=" * 70)

    # 1. Validacion
    print("\n[1] Validacion estructural del workflow")
    validation = ValidateWorkflow().execute(ValidateWorkflowInput(workflow=wf))
    print(f"    Valido: {validation.is_valid}")
    print(f"    Errores: {validation.error_count} | Warnings: {validation.warning_count}")
    for issue in validation.issues:
        prefix = "ERROR" if issue.is_error else "WARN "
        print(f"    {prefix} [{issue.node_id}] {issue.message}")

    # 2. Ejecucion con tres queries diferentes
    processor = EmbeddingProcessor()
    use_case = ExecuteWorkflow(semantic_processor=processor)

    queries = [
        "authentication failure detected on login",
        "network timeout connecting to database",
        "validation error invalid input email",
    ]

    for query in queries:
        print(f"\n[2] Ejecutando workflow con query: '{query}'")
        out = use_case.execute(ExecuteWorkflowInput(workflow=wf, branch_query=query))
        result = out.result
        visited = [str(r.node_id) for r in result.node_results]
        print(f"    Status: {result.status.value}")
        print(f"    Success: {out.success}")
        print(f"    Nodos visitados: {' -> '.join(visited)}")
        print(f"    Pasados: {result.passed_count} | Fallidos: {result.failed_count}")
        print(f"    Success rate: {result.success_rate:.0%}")
        print(f"    Duracion: {result.duration_ms} ms")

    # 3. Caso de fallo: query que no matchea ningun branch
    print(f"\n[3] Query ambiguo (sin match claro)")
    out = use_case.execute(ExecuteWorkflowInput(workflow=wf, branch_query="random unknown topic"))
    visited = [str(r.node_id) for r in out.result.node_results]
    print(f"    Status: {out.result.status.value}")
    print(f"    Nodos visitados: {' -> '.join(visited) or '(solo start)'}")
    print(f"    Nota: si ningun branch supera el umbral, el workflow")
    print(f"    termina sin visitar los handlers.")


if __name__ == "__main__":
    run_demo()
