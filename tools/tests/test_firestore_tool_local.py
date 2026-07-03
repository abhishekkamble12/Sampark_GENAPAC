"""
Unit tests for tools/firestore_tool.py local in-memory DB functionality.
"""

from __future__ import annotations

import pytest
from tools.firestore_tool import FirestoreTool


@pytest.fixture(autouse=True)
def clean_local_db():
    """Clear the local in-memory DB before each test."""
    FirestoreTool._local_db.clear()


@pytest.mark.asyncio
async def test_local_crud_operations():
    tool = FirestoreTool(db=None)

    # 1. Get non-existent
    doc = await tool.get_document("issues", "iss_1")
    assert doc is None

    # 2. Set document
    data = {"type": "road", "status": "open", "description": "Pothole on MG Road"}
    await tool.set_document("issues", "iss_1", data)

    doc = await tool.get_document("issues", "iss_1")
    assert doc is not None
    assert doc["id"] == "iss_1"
    assert doc["type"] == "road"
    assert doc["description"] == "Pothole on MG Road"

    # 3. Update document
    await tool.update_document("issues", "iss_1", {"status": "resolved"})
    doc = await tool.get_document("issues", "iss_1")
    assert doc["status"] == "resolved"
    assert doc["type"] == "road"  # untouched

    # 4. Set document with merge
    await tool.set_document("issues", "iss_1", {"severity": "High"}, merge=True)
    doc = await tool.get_document("issues", "iss_1")
    assert doc["severity"] == "High"
    assert doc["status"] == "resolved"

    # 5. Delete document
    await tool.delete_document("issues", "iss_1")
    doc = await tool.get_document("issues", "iss_1")
    assert doc is None


@pytest.mark.asyncio
async def test_local_geo_radius_query():
    tool = FirestoreTool(db=None)

    # Pune coordinates center
    centre_lat, centre_lng = 18.5204, 73.8567

    # 1. Document 100 meters away (approx 0.0009 deg)
    await tool.set_document("issues", "iss_near", {
        "type": "road",
        "status": "open",
        "location": {"lat": 18.5204 + 0.0005, "lng": 73.8567 + 0.0005}
    })

    # 2. Document 2 km away
    await tool.set_document("issues", "iss_far", {
        "type": "road",
        "status": "open",
        "location": {"lat": 18.5204 + 0.015, "lng": 73.8567 + 0.015}
    })

    # 3. Document 100 meters away with different type
    await tool.set_document("issues", "iss_other_type", {
        "type": "flood",
        "status": "open",
        "lat": 18.5204 - 0.0005,
        "lng": 73.8567 - 0.0005
    })

    # Query within 500 meters
    results = await tool.geo_radius_query(
        collection="issues",
        lat=centre_lat,
        lng=centre_lng,
        radius_meters=500,
        filters={"status": "open", "type": "road"}
    )

    assert len(results) == 1
    assert results[0]["id"] == "iss_near"

    # Query with type filter flood
    results_flood = await tool.geo_radius_query(
        collection="issues",
        lat=centre_lat,
        lng=centre_lng,
        radius_meters=500,
        filters={"type": "flood"}
    )
    assert len(results_flood) == 1
    assert results_flood[0]["id"] == "iss_other_type"


@pytest.mark.asyncio
async def test_local_chunk_metadata():
    tool = FirestoreTool(db=None)

    chunks = [
        {"doc_name": "policy.pdf", "chunk_index": 0, "content": "Chunk 0"},
        {"doc_name": "policy.pdf", "chunk_index": 1, "content": "Chunk 1"},
    ]

    await tool.save_document_chunks("policy.pdf", chunks)

    meta = await tool.get_chunk_metadata("policy.pdf", 0)
    assert meta is not None
    assert meta["content"] == "Chunk 0"

    all_chunks = await tool.get_document_chunks("policy.pdf")
    assert len(all_chunks) == 2

    await tool.delete_document_metadata("policy.pdf")
    all_chunks_after = await tool.get_document_chunks("policy.pdf")
    assert len(all_chunks_after) == 0
