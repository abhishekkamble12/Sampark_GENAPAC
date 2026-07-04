"""
tools/vertex_tool.py — Vertex AI Vector Search tool for Sampark AI.
"""
from typing import Any, List, Dict
import logging

try:
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
except ImportError:
    aiplatform = None
    TextEmbeddingModel = None

logger = logging.getLogger(__name__)

class VertexSearchTool:
    def __init__(self, project_id: str, location: str = "us-central1", index_endpoint_id: str = "", deployed_index_id: str = ""):
        self.project_id = project_id
        self.location = location
        self.index_endpoint_id = index_endpoint_id
        self.deployed_index_id = deployed_index_id
        
        try:
            from backend.config import settings
            is_local = settings.APP_MODE == "local"
        except Exception:
            is_local = False

        if aiplatform and not is_local:
            aiplatform.init(project=project_id, location=location)
            try:
                self._model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
            except Exception:
                self._model = None
                
            if self.index_endpoint_id:
                try:
                    self._index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=self.index_endpoint_id)
                except Exception:
                    self._index_endpoint = None
            else:
                self._index_endpoint = None
        else:
            self._model = None
            self._index_endpoint = None


    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self._model:
            return [[0.1] * 768 for _ in texts]
        import asyncio
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, self._model.get_embeddings, texts)
        return [e.values for e in embeddings]

    async def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> None:
        if not self._index_endpoint:
            return
        
        datapoints = []
        for v in vectors:
            datapoints.append(
                aiplatform.matching_engine.matching_engine_index_endpoint.IndexDatapoint(
                    datapoint_id=v["id"],
                    feature_vector=v["embedding"]
                )
            )
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, 
            self._index_endpoint.upsert_datapoints, 
            self.deployed_index_id, 
            datapoints
        )

    async def search_vectors(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        from backend.config import settings
        if not self._index_endpoint or settings.APP_MODE == "local":
            return [{"id": "road_repair_act_0", "score": 0.85}]

        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._index_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k
            )
        )
        
        results = []
        for neighbors in response:
            for neighbor in neighbors:
                results.append({"id": neighbor.id, "score": neighbor.distance})
        return results

    async def delete_vectors(self, ids: List[str]) -> None:
        if not self._index_endpoint:
            return
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._index_endpoint.remove_datapoints,
            self.deployed_index_id,
            ids
        )
