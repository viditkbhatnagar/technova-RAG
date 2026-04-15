"""GET /api/graph — return the cached knowledge graph for 3D visualization."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/api/graph")
def get_knowledge_graph(request: Request) -> dict:
    """Return the in-memory knowledge graph built during ingestion.

    The graph is cached on app.state.graph_data after each /api/ingest run.
    If ingestion hasn't happened yet, return 404 with instructions.
    """
    graph_data = getattr(request.app.state, "graph_data", None)
    if not graph_data:
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph not built. Call POST /api/ingest first.",
        )
    return graph_data
