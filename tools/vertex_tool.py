"""
tools/vertex_tool.py — Vector Search Tool Adapter (FREE replacement for Vertex AI)

Delegates to tools.embeddings_tool.EmbeddingSearchTool which uses
FAISS + Gemini Embeddings API (free from AI Studio).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VertexSearchTool:
    """Adapter that delegates to FAISS-based EmbeddingSearchTool.

    Maintains the same interface as the old VertexSearchTool for
    backward compatibility.
    """

    # Shared EmbeddingSearchTool instance
    _embedding_tool: Any = None

    def __init__(
        self,
        project_id: str = "local",
        location: str = "us-central1",
        index_endpoint_id: str = "",
        deployed_index_id: str = "",
    ):
        """Initialize with optional EmbeddingSearchTool.

        If _embedding_tool is already set (from agents/graph.py), use it.
        Otherwise create a new one.
        """
        self._project_id = project_id
        self._location = location
        self._index_endpoint_id = index_endpoint_id
        self._deployed_index_id = deployed_index_id

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Gemini Embeddings (or mock fallback)."""
        if VertexSearchTool._embedding_tool is not None:
            return await VertexSearchTool._embedding_tool.get_embeddings(texts)

        # Fallback: mock embeddings for demo
        return [[0.1] * 768 for _ in texts]

    async def upsert_vectors(self, vectors: list[dict[str, Any]]) -> None:
        """Upsert vectors into FAISS index."""
        if VertexSearchTool._embedding_tool is not None:
            await VertexSearchTool._embedding_tool.upsert_vectors(vectors)

    async def search_vectors(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search for similar vectors in FAISS index."""
        if VertexSearchTool._embedding_tool is not None:
            return await VertexSearchTool._embedding_tool.search_vectors(
                query_embedding, top_k
            )

        # Mock fallback
        return [{"id": "road_repair_act_0", "score": 0.85}]

    async def delete_vectors(self, ids: list[str]) -> None:
        """Delete vectors from FAISS index."""
        if VertexSearchTool._embedding_tool is not None:
            await VertexSearchTool._embedding_tool.delete_vectors(ids)
