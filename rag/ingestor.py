"""
rag/ingestor.py — RAG Pipeline Document Ingestion.

Parses PDFs (mocked), chunks them into 512-token segments with 64-token overlap,
and simulates upserting to Vertex AI Vector Search and Firestore.
"""

from __future__ import annotations

import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
OVERLAP_SIZE = 64

class DocumentChunk:
    def __init__(self, doc_name: str, page_number: int, chunk_index: int, text: str):
        self.doc_name = doc_name
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.text = text
        
        # Simple word split for token count heuristic
        self.token_count = len(text.split())
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_name": self.doc_name,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count
        }

class MockPdfReader:
    """Mock for pypdf.PdfReader to extract text page-by-page."""
    def __init__(self, file_bytes: bytes):
        # Decode bytes just to simulate reading text, fallback to generic
        try:
            content = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = "Mocked PDF content fallback."
            
        # Pretend we split it into pages by double newline
        pages = content.split('\n\n')
        self.pages = [type('Page', (), {'extract_text': lambda self=self, t=p: t})() for p in pages if p.strip()]
        
        if not self.pages:
            self.pages = [type('Page', (), {'extract_text': lambda self=self: "Empty page"})()]

class Ingestor:
    """Handles parsing, chunking, and storage of documents."""
    
    def __init__(self, vertex_ai_client: Any, firestore_client: Any):
        self.vertex = vertex_ai_client
        self.firestore = firestore_client
        
    def chunk_text(self, text: str, doc_name: str, page_number: int, start_chunk_idx: int) -> List[DocumentChunk]:
        """Split text into 512 token chunks with 64 token overlap."""
        words = text.split()
        chunks = []
        
        if not words:
            return chunks
            
        step = CHUNK_SIZE - OVERLAP_SIZE
        
        chunk_idx = start_chunk_idx
        for i in range(0, len(words), step):
            chunk_words = words[i : i + CHUNK_SIZE]
            chunk_text = " ".join(chunk_words)
            chunks.append(DocumentChunk(
                doc_name=doc_name,
                page_number=page_number,
                chunk_index=chunk_idx,
                text=chunk_text
            ))
            chunk_idx += 1
            
            # If we exactly hit the end or overshot, break to avoid trailing tiny overlaps
            if i + CHUNK_SIZE >= len(words):
                break
                
        return chunks

    async def ingest_pdf(self, doc_name: str, file_bytes: bytes) -> bool:
        """Parse PDF, chunk, embed, and store."""
        try:
            reader = MockPdfReader(file_bytes)
        except Exception:
            logger.exception("Failed to parse PDF %s", doc_name)
            return False
            
        all_chunks: List[DocumentChunk] = []
        chunk_idx = 0
        
        # 9.1 & 9.2 PDF parsing and deterministic chunking
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                page_chunks = self.chunk_text(text, doc_name, page_num, chunk_idx)
                all_chunks.extend(page_chunks)
                chunk_idx += len(page_chunks)
                
        if not all_chunks:
            return True
            
        try:
            # 9.3 Embeddings mock
            texts = [c.text for c in all_chunks]
            embeddings = await self.vertex.get_embeddings(texts)
            
            # 9.4 Vector Search upsert mock
            vector_items = []
            for i, chunk in enumerate(all_chunks):
                vector_items.append({
                    "id": f"{doc_name}_{chunk.chunk_index}",
                    "embedding": embeddings[i]
                })
            await self.vertex.upsert_vectors(vector_items)
            
            # 9.5 Firestore metadata storage mock
            doc_metadata = [c.to_dict() for c in all_chunks]
            await self.firestore.save_document_chunks(doc_name, doc_metadata)
            
            return True
        except Exception:
            # 9.6 Handle failures
            logger.exception("Ingestion failed for %s during embedding/storage", doc_name)
            return False

    async def delete_document_cascade(self, doc_name: str) -> bool:
        """15.2 Mock cascade delete from Vector Search and Firestore."""
        try:
            # First, fetch metadata to know which chunk IDs to delete from Vector Search
            chunks = await self.firestore.get_document_chunks(doc_name)
            if chunks:
                chunk_ids = [f"{doc_name}_{c.get('chunk_index')}" for c in chunks]
                await self.vertex.delete_vectors(chunk_ids)
            
            # Finally, delete metadata
            await self.firestore.delete_document_metadata(doc_name)
            return True
        except Exception:
            logger.exception("Cascade delete failed for %s", doc_name)
            return False
