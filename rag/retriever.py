"""
rag/retriever.py — RAG Pipeline Document Retrieval (FREE Stack)

Retrieves chunks using FAISS ANN with a 0.75 score threshold.
Uses Gemini Embeddings for query encoding (free from AI Studio).

Replaces Vertex AI Vector Search with FAISS (local, free).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves policy document chunks using FAISS vector search.

    Uses the same interface as the original Retriever but backed by
    FAISS + Gemini Embeddings instead of Vertex AI Vector Search.
    """

    def __init__(self, vertex_ai_client: Any, firestore_client: Any):
        self.vertex = vertex_ai_client
        self.firestore = firestore_client

    async def retrieve(self, query: str) -> tuple[list[dict[str, Any]], bool]:
        """Search for top 5 chunks relevant to the query.

        Returns:
            Tuple of (chunks_list, no_policy_context_flag).
        """
        try:
            from backend.config import settings

            if settings.APP_MODE == "local":
                # Local mode: return mock chunks based on keywords
                q_lower = query.lower()
                if "flood" in q_lower or "drain" in q_lower:
                    doc_name, chunk_idx = "urban_flood_guidelines", 0
                elif "water" in q_lower or "leak" in q_lower:
                    doc_name, chunk_idx = "water_leakage_protocol", 0
                else:
                    doc_name, chunk_idx = "road_maintenance_policy", 0

                metadata = await self.firestore.get_chunk_metadata(doc_name, chunk_idx)
                if metadata:
                    return [metadata], False
                return [], True

            # Production mode: Embed query using Gemini Embeddings (free)
            query_embedding = (await self.vertex.get_embeddings([query]))[0]

            # Search FAISS index
            results = await self.vertex.search_vectors(query_embedding, top_k=5)

            # Filter by relevance score threshold
            # For L2 distance, lower is better. Threshold of ~1.0 is reasonable.
            valid_results = [r for r in results if r["score"] < 1.0]

            if not valid_results:
                return [], True

            # Fetch metadata from SQLite
            chunks = []
            for r in valid_results:
                chunk_id = r["id"]
                # id format: {doc_name}_{chunk_index}
                doc_name, chunk_idx = chunk_id.rsplit("_", 1)
                try:
                    chunk_idx_int = int(chunk_idx)
                except ValueError:
                    continue

                metadata = await self.firestore.get_chunk_metadata(doc_name, chunk_idx_int)
                if metadata:
                    chunks.append(metadata)

            return chunks, False

        except Exception:
            logger.exception("Retrieval failed")
            return [], True
