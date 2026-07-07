"""
rag/retriever.py — RAG Pipeline Document Retrieval.

Retrieves chunks using mock Vector Search ANN with a 0.75 score threshold.
"""

from __future__ import annotations

import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, vertex_ai_client: Any, firestore_client: Any):
        self.vertex = vertex_ai_client
        self.firestore = firestore_client
        
    async def retrieve(self, query: str) -> tuple[List[Dict[str, Any]], bool]:
        """Search for top 5 chunks with ANN score > 0.75.
        
        Returns:
            Tuple of (chunks_list, no_policy_context_flag).
        """
        try:
            from backend.config import settings
            if settings.APP_MODE == "local":
                q_lower = query.lower()
                import re
                words = set(re.findall(r'\b[a-z]{3,}\b', q_lower))
                
                from tools.firestore_tool import FirestoreTool
                all_kb = FirestoreTool._local_db.get("knowledge_base", {})
                
                scored_chunks = []
                for chunk_id, chunk in all_kb.items():
                    text = chunk.get("text", "").lower()
                    doc_name = chunk.get("doc_name", "").lower()
                    
                    score = 0
                    for word in words:
                        if word in text:
                            score += text.count(word) * 2
                        if word in doc_name:
                            score += doc_name.count(word) * 5
                            
                    if score > 0:
                        scored_chunks.append((score, chunk))
                        
                if scored_chunks:
                    # Sort by score descending
                    scored_chunks.sort(key=lambda x: x[0], reverse=True)
                    return [item[1] for item in scored_chunks[:3]], False
                
                # Fallback to defaults
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

            # 9.7 Embed query and ANN search
            query_embedding = (await self.vertex.get_embeddings([query]))[0]
            
            # search_vectors returns list of {"id": str, "score": float}
            results = await self.vertex.search_vectors(query_embedding, top_k=5)
            
            # Filter by 0.75 threshold
            valid_results = [r for r in results if r["score"] > 0.75]
            
            if not valid_results:
                # 9.8 Empty results flag
                return [], True
                
            # Fetch metadata from Firestore
            chunks = []
            for r in valid_results:
                chunk_id = r["id"]
                # id format: {doc_name}_{chunk_index}
                doc_name, chunk_idx = chunk_id.rsplit('_', 1)
                
                metadata = await self.firestore.get_chunk_metadata(doc_name, int(chunk_idx))
                if metadata:
                    chunks.append(metadata)
                    
            return chunks, False
            
        except Exception:
            logger.exception("Retrieval failed")
            return [], True
