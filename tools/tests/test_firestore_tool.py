"""
Unit tests for tools/firestore_tool.py

The new FirestoreTool uses an in-memory dict (or delegates to SQLite via
DatabaseTool). All tests run without any GCP dependencies.
"""

from __future__ import annotations

import math
import pytest

from tools.firestore_tool import FirestoreTool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_local_db():
    """Clear the local in-memory DB before each test."""
    FirestoreTool._local_db.clear()


@pytest.fixture
def tool():
    return FirestoreTool(db=None)


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document_returns_data_with_id(tool):
    """Existing document is returned as a dict with an id key."""
    await tool.set_document("issues", "iss_abc", {"type": "road", "status": "open"})

    result = await tool.get_document("issues", "iss_abc")

    assert result is not None
    assert result["id"] == "iss_abc"
    assert result["type"] == "road"


@pytest.mark.asyncio
async def test_get_document_returns_none_when_not_found(tool):
    """A non-existent document returns None without raising."""
    result = await tool.get_document("issues", "missing_doc")
    assert result is None


@pytest.mark.asyncio
async def test_set_document_creates_without_merge(tool):
    """set_document with merge=False replaces existing data."""
    await tool.set_document("issues", "iss_1", {"type": "road", "status": "open"})
    await tool.set_document("issues", "iss_1", {"type": "flood", "severity": "high"}, merge=False)

    doc = await tool.get_document("issues", "iss_1")
    # type should be overwritten, status should be gone
    assert doc["type"] == "flood"
    assert "status" not in doc


@pytest.mark.asyncio
async def test_set_document_merges_when_merge_true(tool):
    """merge=True merges new data into existing document."""
    await tool.set_document("issues", "iss_1", {"type": "road", "status": "open"})
    await tool.set_document("issues", "iss_1", {"severity": "high"}, merge=True)

    doc = await tool.get_document("issues", "iss_1")
    assert doc["type"] == "road"  # untouched
    assert doc["severity"] == "high"  # added


@pytest.mark.asyncio
async def test_update_document_modifies_fields(tool):
    """update_document updates specific fields."""
    await tool.set_document("tasks", "task_001", {"status": "open", "priority": "Low"})
    await tool.update_document("tasks", "task_001", {"status": "in_progress", "priority": "High"})

    doc = await tool.get_document("tasks", "task_001")
    assert doc["status"] == "in_progress"
    assert doc["priority"] == "High"


@pytest.mark.asyncio
async def test_update_document_raises_on_missing(tool):
    """update_document raises KeyError if document doesn't exist."""
    with pytest.raises(KeyError):
        await tool.update_document("tasks", "nonexistent", {"status": "open"})


@pytest.mark.asyncio
async def test_delete_document_removes_doc(tool):
    """delete_document removes the document from the collection."""
    await tool.set_document("issues", "iss_old", {"type": "road"})
    await tool.delete_document("issues", "iss_old")

    doc = await tool.get_document("issues", "iss_old")
    assert doc is None


# ---------------------------------------------------------------------------
# Geo-radius query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geo_radius_query_returns_nearby_doc(tool):
    """A document within the radius is returned."""
    centre_lat, centre_lng = 18.52, 73.86

    await tool.set_document("issues", "iss_near", {
        "type": "road",
        "location": {"lat": centre_lat + 0.0005, "lng": centre_lng + 0.0005}
    })

    results = await tool.geo_radius_query("issues", centre_lat, centre_lng, 500)

    assert len(results) == 1
    assert results[0]["id"] == "iss_near"


@pytest.mark.asyncio
async def test_geo_radius_query_excludes_distant_doc(tool):
    """A document beyond the radius is excluded."""
    centre_lat, centre_lng = 18.52, 73.86

    await tool.set_document("issues", "iss_far", {
        "type": "road",
        "location": {"lat": centre_lat + 0.018, "lng": centre_lng + 0.018}
    })

    results = await tool.geo_radius_query("issues", centre_lat, centre_lng, 500)

    assert results == []


@pytest.mark.asyncio
async def test_geo_radius_query_applies_filters(tool):
    """Filters are applied to geo-radius results."""
    centre_lat, centre_lng = 18.52, 73.86

    await tool.set_document("issues", "iss_road", {
        "type": "road",
        "location": {"lat": centre_lat + 0.0005, "lng": centre_lng + 0.0005}
    })
    await tool.set_document("issues", "iss_flood", {
        "type": "flood",
        "location": {"lat": centre_lat + 0.0003, "lng": centre_lng + 0.0003}
    })

    results = await tool.geo_radius_query(
        "issues", centre_lat, centre_lng, 500, filters={"type": "road"}
    )

    assert len(results) == 1
    assert results[0]["type"] == "road"


@pytest.mark.asyncio
async def test_geo_radius_query_skips_doc_missing_lat_or_lng(tool):
    """Documents without lat/lng fields are skipped."""
    centre_lat, centre_lng = 18.52, 73.86

    await tool.set_document("issues", "no_geo", {"type": "road"})

    results = await tool.geo_radius_query("issues", centre_lat, centre_lng, 500)
    assert results == []


@pytest.mark.asyncio
async def test_geo_radius_query_returns_empty_list_gracefully(tool):
    """Geo-query on non-existent collection returns empty list."""
    results = await tool.geo_radius_query("empty_collection", 18.52, 73.86, 500)
    assert results == []


# ---------------------------------------------------------------------------
# RAG helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_document_chunks(tool):
    """save_document_chunks stores chunks under knowledge_base."""
    chunks = [
        {"doc_name": "policy.pdf", "chunk_index": 0, "text": "Chunk 0"},
        {"doc_name": "policy.pdf", "chunk_index": 1, "text": "Chunk 1"},
    ]
    await tool.save_document_chunks("policy.pdf", chunks)

    meta = await tool.get_chunk_metadata("policy.pdf", 0)
    assert meta is not None
    assert meta["text"] == "Chunk 0"


@pytest.mark.asyncio
async def test_get_document_chunks(tool):
    """get_document_chunks returns all chunks for a document."""
    chunks = [
        {"doc_name": "policy.pdf", "chunk_index": 0, "text": "Chunk 0"},
        {"doc_name": "policy.pdf", "chunk_index": 1, "text": "Chunk 1"},
    ]
    await tool.save_document_chunks("policy.pdf", chunks)

    all_chunks = await tool.get_document_chunks("policy.pdf")
    assert len(all_chunks) == 2


@pytest.mark.asyncio
async def test_delete_document_metadata(tool):
    """delete_document_metadata removes all chunks for a document."""
    chunks = [
        {"doc_name": "policy.pdf", "chunk_index": 0, "text": "Chunk 0"},
    ]
    await tool.save_document_chunks("policy.pdf", chunks)
    await tool.delete_document_metadata("policy.pdf")

    remaining = await tool.get_document_chunks("policy.pdf")
    assert len(remaining) == 0


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_overdue_open_tasks(tool):
    """Returns open tasks past their due date."""
    await tool.set_document("tasks", "task_1", {
        "status": "open", "due_date": "2020-01-01T00:00:00Z"
    })
    await tool.set_document("tasks", "task_2", {
        "status": "open", "due_date": "2099-01-01T00:00:00Z"
    })
    await tool.set_document("tasks", "task_3", {
        "status": "resolved", "due_date": "2020-01-01T00:00:00Z"
    })

    overdue = await tool.query_overdue_open_tasks("2025-01-01T00:00:00Z")
    assert len(overdue) == 1
    assert overdue[0]["id"] == "task_1"


@pytest.mark.asyncio
async def test_log_notification(tool):
    """A notification entry is created."""
    await tool.log_notification({
        "channel": "email", "status": "delivered", "target": "user@example.com"
    })

    # Verify it was stored
    logs = await tool.list_documents("notifications")
    assert len(logs) == 1
    assert logs[0]["channel"] == "email"


# ---------------------------------------------------------------------------
# on_snapshot (mock - no-op)
# ---------------------------------------------------------------------------


def test_on_snapshot_returns_callable(tool):
    """on_snapshot must return a callable (unsubscribe function)."""
    unsubscribe = tool.on_snapshot("tasks", callback=lambda *_: None)
    assert callable(unsubscribe)


def test_on_snapshot_unsubscribe_swallows_exceptions(tool):
    """If unsubscribe raises, the exception must be swallowed."""
    unsubscribe = tool.on_snapshot("tasks", callback=lambda *_: None)
    # Should not raise
    unsubscribe()
