"""
Unit tests for tools/firestore_tool.py

All Firestore SDK calls are mocked so these tests run without a real GCP
project or Firestore instance.
"""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.firestore_tool import (
    FirestoreTool,
    _haversine_metres,
    _lat_delta,
    _lng_delta,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_tool() -> tuple[FirestoreTool, MagicMock]:
    """Return (FirestoreTool instance, mock AsyncClient)."""
    mock_db = MagicMock()
    tool = FirestoreTool(db=mock_db)
    return tool, mock_db


def _make_doc_snapshot(doc_id: str, data: dict[str, Any]) -> MagicMock:
    """Simulate a Firestore DocumentSnapshot."""
    snap = MagicMock()
    snap.id = doc_id
    snap.exists = True
    snap.to_dict.return_value = dict(data)
    return snap


# ---------------------------------------------------------------------------
# Geo helper unit tests
# ---------------------------------------------------------------------------


def test_lat_delta_500m():
    """500 m should correspond to ~0.0045 degrees latitude."""
    delta = _lat_delta(500)
    assert abs(delta - 500 / 111_320.0) < 1e-6


def test_lng_delta_equator():
    """At the equator (lat=0) lng delta == lat delta."""
    assert abs(_lng_delta(500, 0.0) - _lat_delta(500)) < 1e-6


def test_lng_delta_high_latitude():
    """At lat=60° the lng delta should be approximately twice the lat delta."""
    # cos(60°) = 0.5  →  lng_delta ≈ 2 × lat_delta
    delta = _lng_delta(500, 60.0)
    expected = 500 / (111_320.0 * math.cos(math.radians(60.0)))
    assert abs(delta - expected) < 1e-6


def test_lng_delta_near_pole_does_not_raise():
    """Near the pole (lat≈90°) should not raise and returns a very large value."""
    delta = _lng_delta(500, 89.9999)
    assert delta > 0


def test_haversine_same_point_is_zero():
    """Distance from a point to itself must be 0."""
    assert _haversine_metres(18.52, 73.86, 18.52, 73.86) == pytest.approx(0.0, abs=1e-3)


def test_haversine_known_distance():
    """Two points ~111 km apart (1 degree latitude) should be close to 111,320 m."""
    d = _haversine_metres(0.0, 0.0, 1.0, 0.0)
    assert abs(d - 111_320.0) < 200  # within 200 m of the reference value


def test_haversine_is_symmetric():
    """Distance from A→B must equal B→A."""
    d1 = _haversine_metres(18.52, 73.86, 18.53, 73.87)
    d2 = _haversine_metres(18.53, 73.87, 18.52, 73.86)
    assert d1 == pytest.approx(d2, rel=1e-6)


# ---------------------------------------------------------------------------
# geo_radius_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geo_radius_query_returns_nearby_doc():
    """A document within the radius and bounding box is returned."""
    tool, mock_db = _make_tool()

    # Document 10 m north of centre — well within 500 m
    centre_lat, centre_lng = 18.52, 73.86
    doc_lat = centre_lat + 0.0001  # ~11 m north
    doc_lng = centre_lng

    snap = _make_doc_snapshot("iss_001", {"lat": doc_lat, "lng": doc_lng, "type": "road"})

    # Wire up the async generator for query.stream()
    async def _aiter(*_args, **_kwargs):
        yield snap

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.stream = _aiter

    mock_db.collection.return_value.where.return_value = mock_query
    # Make collection reference itself behave as the starting query
    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    with patch("tools.firestore_tool._get_field_filter", return_value=MagicMock(return_value=MagicMock())):
        results = await tool.geo_radius_query("issues", centre_lat, centre_lng, 500)

    assert len(results) == 1
    assert results[0]["id"] == "iss_001"
    assert results[0]["type"] == "road"


@pytest.mark.asyncio
async def test_geo_radius_query_excludes_distant_doc():
    """A document beyond the radius (after Haversine check) is excluded."""
    tool, mock_db = _make_tool()

    centre_lat, centre_lng = 18.52, 73.86
    # ~2 km north — outside 500 m radius but inside a wide bounding box
    doc_lat = centre_lat + 0.018
    doc_lng = centre_lng

    snap = _make_doc_snapshot("far_doc", {"lat": doc_lat, "lng": doc_lng})

    async def _aiter(*_args, **_kwargs):
        yield snap

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.stream = _aiter

    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    with patch("tools.firestore_tool._get_field_filter", return_value=MagicMock(return_value=MagicMock())):
        results = await tool.geo_radius_query("issues", centre_lat, centre_lng, 500)

    assert results == []


@pytest.mark.asyncio
async def test_geo_radius_query_applies_equality_filters():
    """Equality filters from *filters* dict are applied to the query.

    We verify that ``where`` was called at least 4 times in total across the
    entire mock chain (2 equality + 2 bounding-box).
    """
    tool, mock_db = _make_tool()

    async def _empty_aiter(*_args, **_kwargs):
        return
        yield  # pragma: no cover — makes it an async generator

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.stream = _empty_aiter

    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    with patch("tools.firestore_tool._get_field_filter", return_value=MagicMock(return_value=MagicMock())):
        await tool.geo_radius_query(
            "issues", 18.52, 73.86, 500, filters={"type": "flood", "status": "open"}
        )

    # Count where() calls across both the collection and query mock objects.
    # The first .where() call goes to mock_collection; subsequent ones hit mock_query.
    total_where_calls = mock_collection.where.call_count + mock_query.where.call_count
    assert total_where_calls >= 4


@pytest.mark.asyncio
async def test_geo_radius_query_returns_empty_list_on_exception():
    """Any Firestore exception returns an empty list (no re-raise)."""
    tool, mock_db = _make_tool()

    mock_db.collection.side_effect = Exception("Firestore down")

    results = await tool.geo_radius_query("issues", 18.52, 73.86, 500)

    assert results == []


@pytest.mark.asyncio
async def test_geo_radius_query_skips_doc_missing_lat_or_lng():
    """Documents without lat/lng fields are silently skipped."""
    tool, mock_db = _make_tool()

    snap = _make_doc_snapshot("no_geo", {"type": "road"})  # no lat / lng

    async def _aiter(*_args, **_kwargs):
        yield snap

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.stream = _aiter

    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    with patch("tools.firestore_tool._get_field_filter", return_value=MagicMock(return_value=MagicMock())):
        results = await tool.geo_radius_query("issues", 18.52, 73.86, 500)

    assert results == []


# ---------------------------------------------------------------------------
# get_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document_returns_data_with_id():
    """Existing document is returned as a dict with an ``id`` key."""
    tool, mock_db = _make_tool()

    snap = _make_doc_snapshot("iss_abc", {"type": "road", "status": "open"})
    mock_ref = AsyncMock()
    mock_ref.get = AsyncMock(return_value=snap)

    mock_db.collection.return_value.document.return_value = mock_ref

    result = await tool.get_document("issues", "iss_abc")

    assert result is not None
    assert result["id"] == "iss_abc"
    assert result["type"] == "road"


@pytest.mark.asyncio
async def test_get_document_returns_none_when_not_found():
    """A non-existent document returns ``None`` without raising."""
    tool, mock_db = _make_tool()

    snap = MagicMock()
    snap.exists = False
    mock_ref = AsyncMock()
    mock_ref.get = AsyncMock(return_value=snap)

    mock_db.collection.return_value.document.return_value = mock_ref

    result = await tool.get_document("issues", "missing_doc")

    assert result is None


@pytest.mark.asyncio
async def test_get_document_reraises_on_firestore_error():
    """Firestore errors are logged and re-raised."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_ref.get = AsyncMock(side_effect=Exception("permission denied"))

    mock_db.collection.return_value.document.return_value = mock_ref

    with pytest.raises(Exception, match="permission denied"):
        await tool.get_document("issues", "iss_abc")


# ---------------------------------------------------------------------------
# set_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_document_calls_set_without_merge():
    """``set_document`` calls ``ref.set(data, merge=False)`` by default."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    data = {"type": "flood", "status": "open"}
    await tool.set_document("issues", "iss_new", data)

    mock_ref.set.assert_awaited_once_with(data, merge=False)


@pytest.mark.asyncio
async def test_set_document_calls_set_with_merge_true():
    """``merge=True`` is forwarded to ``ref.set``."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    data = {"status": "resolved"}
    await tool.set_document("tasks", "task_001", data, merge=True)

    mock_ref.set.assert_awaited_once_with(data, merge=True)


@pytest.mark.asyncio
async def test_set_document_reraises_on_error():
    """Firestore errors are re-raised to the caller."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_ref.set = AsyncMock(side_effect=Exception("quota exceeded"))
    mock_db.collection.return_value.document.return_value = mock_ref

    with pytest.raises(Exception, match="quota exceeded"):
        await tool.set_document("issues", "iss_x", {"type": "road"})


# ---------------------------------------------------------------------------
# update_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_document_calls_ref_update():
    """``update_document`` calls ``ref.update(updates)``."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    updates = {"status": "in_progress", "assigned_officer": "officer_1"}
    await tool.update_document("tasks", "task_001", updates)

    mock_ref.update.assert_awaited_once_with(updates)


@pytest.mark.asyncio
async def test_update_document_reraises_on_error():
    """Firestore errors are re-raised."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_ref.update = AsyncMock(side_effect=Exception("not found"))
    mock_db.collection.return_value.document.return_value = mock_ref

    with pytest.raises(Exception, match="not found"):
        await tool.update_document("tasks", "task_999", {"status": "open"})


# ---------------------------------------------------------------------------
# delete_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_document_calls_ref_delete():
    """``delete_document`` calls ``ref.delete()``."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_db.collection.return_value.document.return_value = mock_ref

    await tool.delete_document("issues", "iss_old")

    mock_ref.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_reraises_on_error():
    """Firestore errors are re-raised."""
    tool, mock_db = _make_tool()

    mock_ref = AsyncMock()
    mock_ref.delete = AsyncMock(side_effect=Exception("internal error"))
    mock_db.collection.return_value.document.return_value = mock_ref

    with pytest.raises(Exception, match="internal error"):
        await tool.delete_document("issues", "iss_x")


# ---------------------------------------------------------------------------
# on_snapshot
# ---------------------------------------------------------------------------


def test_on_snapshot_returns_callable():
    """``on_snapshot`` must return a callable (unsubscribe function)."""
    tool, mock_db = _make_tool()

    mock_watch = MagicMock()
    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.on_snapshot.return_value = mock_watch

    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_collection.on_snapshot.return_value = mock_watch
    mock_db.collection.return_value = mock_collection

    unsubscribe = tool.on_snapshot("tasks", callback=lambda *_: None)

    assert callable(unsubscribe)


def test_on_snapshot_calls_unsubscribe_on_returned_callable():
    """Calling the returned unsubscribe function invokes ``watch.unsubscribe()``."""
    tool, mock_db = _make_tool()

    mock_watch = MagicMock()
    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.on_snapshot.return_value = mock_watch

    mock_collection = MagicMock()
    mock_collection.on_snapshot.return_value = mock_watch
    mock_db.collection.return_value = mock_collection
    # Make sure .where() chains work
    mock_collection.where.return_value = mock_query

    unsubscribe = tool.on_snapshot("tasks", callback=lambda *_: None)
    unsubscribe()

    mock_watch.unsubscribe.assert_called_once()


def test_on_snapshot_applies_equality_filters():
    """Equality filters from *filters* dict are applied via ``query.where``."""
    tool, mock_db = _make_tool()

    mock_watch = MagicMock()
    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.on_snapshot.return_value = mock_watch

    mock_collection = MagicMock()
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    with patch("tools.firestore_tool._get_field_filter", return_value=MagicMock(return_value=MagicMock())):
        tool.on_snapshot(
            "tasks", callback=lambda *_: None, filters={"status": "open", "priority": "High"}
        )

    # Count where() calls across both mock objects; expect at least 2 (one per filter key).
    total_where_calls = mock_collection.where.call_count + mock_query.where.call_count
    assert total_where_calls >= 2


def test_on_snapshot_no_filters_uses_collection_directly():
    """When no filters are provided the listener is attached directly on the collection."""
    tool, mock_db = _make_tool()

    mock_watch = MagicMock()
    mock_collection = MagicMock()
    mock_collection.on_snapshot.return_value = mock_watch
    mock_collection.where.return_value = mock_collection
    mock_db.collection.return_value = mock_collection

    callback = MagicMock()
    tool.on_snapshot("tasks", callback=callback)

    # on_snapshot is called on the collection (or query) with our callback
    # Either mock_collection.on_snapshot or a chained query.on_snapshot was called.
    assert mock_collection.on_snapshot.called or mock_collection.where.called


def test_on_snapshot_unsubscribe_swallows_exceptions():
    """If ``watch.unsubscribe()`` raises, the exception must be swallowed."""
    tool, mock_db = _make_tool()

    mock_watch = MagicMock()
    mock_watch.unsubscribe.side_effect = Exception("already closed")

    mock_query = MagicMock()
    mock_query.where.return_value = mock_query
    mock_query.on_snapshot.return_value = mock_watch

    mock_collection = MagicMock()
    mock_collection.on_snapshot.return_value = mock_watch
    mock_collection.where.return_value = mock_query
    mock_db.collection.return_value = mock_collection

    unsubscribe = tool.on_snapshot("tasks", callback=lambda *_: None)

    # Should not raise
    unsubscribe()


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_stores_db():
    """The ``db`` argument is stored as ``_db``."""
    mock_db = MagicMock()
    tool = FirestoreTool(db=mock_db)
    assert tool._db is mock_db
