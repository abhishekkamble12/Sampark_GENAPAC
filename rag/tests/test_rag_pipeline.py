"""Unit tests for the RAG pipeline (Tasks 9.1 - 9.11)."""

import pytest
import json
from rag.ingestor import Ingestor, DocumentChunk, CHUNK_SIZE, OVERLAP_SIZE
from rag.retriever import Retriever
from rag.generator import Generator

class _MockVertexAI:
    def __init__(self, embeddings_to_return=None, search_results=None):
        self.embeddings = embeddings_to_return or []
        self.search_results = search_results or []
        self.upserted = []
    async def get_embeddings(self, texts):
        return self.embeddings if self.embeddings else [[0.1]*768 for _ in texts]
    async def upsert_vectors(self, vectors):
        self.upserted.extend(vectors)
    async def search_vectors(self, query_emb, top_k=5):
        return self.search_results

class _MockFirestore:
    def __init__(self):
        self.chunks = {}
    async def save_document_chunks(self, doc_name, chunks):
        for c in chunks:
            self.chunks[f"{doc_name}_{c['chunk_index']}"] = c
    async def get_chunk_metadata(self, doc_name, chunk_idx):
        return self.chunks.get(f"{doc_name}_{chunk_idx}")

class _MockGemini:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
    def generate_content(self, prompt):
        if self.should_fail:
            raise Exception("Gemini API down")
        # Extract doc names from prompt to mock a smart citation
        import re
        docs = set(re.findall(r"\[Document:\s*(.*?),\s*Page", prompt))
        resp = {
            "action": "Fix it.",
            "rationale": "Because the policy says so.",
            "cited_policies": list(docs)
        }
        return type('obj', (object,), {'text': json.dumps(resp)})()

@pytest.mark.asyncio
async def test_ingestor_chunking_logic():
    # 9.1 & 9.2: Test 512 token chunking with 64 token overlap
    # We'll use a small version to test the math: say chunk=5, overlap=2
    import rag.ingestor
    rag.ingestor.CHUNK_SIZE = 5
    rag.ingestor.OVERLAP_SIZE = 2
    
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9"
    ingestor = Ingestor(_MockVertexAI(), _MockFirestore())
    chunks = ingestor.chunk_text(text, "doc1", 1, 0)
    
    assert len(chunks) == 3
    # Step = 5 - 2 = 3
    # chunk 0: words 0-4 (word1..word5)
    # chunk 1: words 3-7 (word4..word8)
    # chunk 2: words 6-9 (word7..word9) -> short chunk at end
    assert chunks[0].text == "word1 word2 word3 word4 word5"
    assert chunks[1].text == "word4 word5 word6 word7 word8"
    assert chunks[2].text == "word7 word8 word9"
    
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[2].chunk_index == 2
    
    # Restore constants
    rag.ingestor.CHUNK_SIZE = 512
    rag.ingestor.OVERLAP_SIZE = 64

@pytest.mark.asyncio
async def test_retriever_empty_results():
    # 9.8 Empty list + no_policy_context = true if results < 0.75
    mock_vertex = _MockVertexAI(search_results=[{"id": "doc_0", "score": 0.5}])
    retriever = Retriever(mock_vertex, _MockFirestore())
    
    chunks, no_policy = await retriever.retrieve("query")
    assert chunks == []
    assert no_policy is True

@pytest.mark.asyncio
async def test_generator_failure_bubbling():
    # 9.10 Handle Gemini failure by raising explicit error
    gen = Generator(_MockGemini(should_fail=True))
    with pytest.raises(RuntimeError, match="Generation error: Gemini API down"):
        await gen.generate_recommendation("issue", [{"doc_name": "d1", "page_number": 1, "text": "text"}])
