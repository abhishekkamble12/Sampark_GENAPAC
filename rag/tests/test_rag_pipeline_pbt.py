"""Property-based tests for RAG Pipeline."""

import asyncio
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rag.ingestor import Ingestor, CHUNK_SIZE, OVERLAP_SIZE
from rag.retriever import Retriever
from rag.tests.test_rag_pipeline import _MockVertexAI, _MockFirestore

@given(
    st.text(min_size=100, max_size=10000, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')))
)
@settings(max_examples=20)
def test_retrieval_finds_verbatim_sentence(pdf_text):
    """9.12 For any valid PDF, retrieving a verbatim sentence returns >= 1 chunk."""
    words = pdf_text.split()
    if len(words) < 10:
        return # Skip too short
        
    # Grab a 10-word sentence from the middle
    mid = len(words) // 2
    sentence = " ".join(words[mid:mid+10])
    
    async def _run():
        vertex = _MockVertexAI()
        fs = _MockFirestore()
        ing = Ingestor(vertex, fs)
        
        # 1. Ingest
        # We mock pdf bytes, but the mock reader splits by \n\n. Let's just pass raw text directly to chunk_text
        chunks = ing.chunk_text(pdf_text, "test_doc", 1, 0)
        await fs.save_document_chunks("test_doc", [c.to_dict() for c in chunks])
        
        # We simulate the search returning exactly the chunk that contains the sentence with a 0.9 score
        found_chunk_id = None
        for c in chunks:
            if sentence in c.text:
                found_chunk_id = f"test_doc_{c.chunk_index}"
                break
                
        assert found_chunk_id is not None, "Sentence not found in any chunk! Overlap logic failure."
        
        vertex.search_results = [{"id": found_chunk_id, "score": 0.9}]
        
        # 2. Retrieve
        retriever = Retriever(vertex, fs)
        res_chunks, no_policy = await retriever.retrieve(sentence)
        
        assert not no_policy
        assert len(res_chunks) >= 1
        assert res_chunks[0]["doc_name"] == "test_doc"
        assert sentence in res_chunks[0]["text"]
        
    asyncio.run(_run())
