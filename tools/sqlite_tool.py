"""
tools/sqlite_tool.py — SQLite Database Tool (FREE replacement for Firestore)

Provides async CRUD operations, geo-radius queries, and document storage
for the Sampark AI Platform using aiosqlite.

Runs entirely locally with zero cloud dependencies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from typing import Any, Callable
import aiosqlite

logger = logging.getLogger(__name__)

_METRES_PER_LAT_DEGREE: float = 111_320.0


def _lat_delta(radius_metres: float) -> float:
    return radius_metres / _METRES_PER_LAT_DEGREE


def _lng_delta(radius_metres: float, lat: float) -> float:
    cos_lat = math.cos(math.radians(lat))
    if cos_lat < 1e-9:
        return 180.0
    return radius_metres / (_METRES_PER_LAT_DEGREE * cos_lat)


def _haversine_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DatabaseTool:
    """Async SQLite wrapper replacing Firestore for the Sampark AI Platform.

    Stores documents as JSON blobs in collections, enabling schema-less
    document storage similar to Firestore but completely local and free.
    """

    def __init__(self, db_path: str = "data/sampark.db"):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._local_db: dict[str, dict[str, dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Create the database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                collection_name TEXT NOT NULL,
                document_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (collection_name, document_id)
            )
        """)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS geo_index (
                collection_name TEXT NOT NULL,
                document_id TEXT NOT NULL,
                lat REAL,
                lng REAL,
                PRIMARY KEY (collection_name, document_id)
            )
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collection
            ON collections(collection_name)
        """)
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo
            ON geo_index(collection_name, lat, lng)
        """)

        await self._conn.commit()
        logger.info("SQLite database initialized at %s", self._db_path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _ensure_initialized(self) -> None:
        if self._conn is None:
            await self.initialize()

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------

    async def set_document(
        self, collection: str, doc_id: str, data: dict[str, Any], merge: bool = False
    ) -> None:
        """Set a document, optionally merging with existing data."""
        await self._ensure_initialized()

        if merge:
            existing = await self.get_document(collection, doc_id)
            if existing:
                existing.update(data)
                data = existing

        data_json = json.dumps(data, default=str)
        await self._conn.execute(
            """INSERT OR REPLACE INTO collections
               (collection_name, document_id, data, updated_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (collection, doc_id, data_json),
        )

        # Update geo index if lat/lng present
        loc = data.get("location") or {}
        lat = loc.get("lat") or data.get("lat")
        lng = loc.get("lng") or data.get("lng")
        if lat is not None and lng is not None:
            await self._conn.execute(
                """INSERT OR REPLACE INTO geo_index
                   (collection_name, document_id, lat, lng)
                   VALUES (?, ?, ?, ?)""",
                (collection, doc_id, float(lat), float(lng)),
            )

        await self._conn.commit()

    async def get_document(
        self, collection: str, doc_id: str
    ) -> dict[str, Any] | None:
        """Retrieve a document by ID."""
        await self._ensure_initialized()

        cursor = await self._conn.execute(
            "SELECT data FROM collections WHERE collection_name = ? AND document_id = ?",
            (collection, doc_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        data = json.loads(row["data"])
        data["id"] = doc_id
        return data

    async def update_document(
        self, collection: str, doc_id: str, updates: dict[str, Any]
    ) -> None:
        """Update specific fields of a document."""
        existing = await self.get_document(collection, doc_id)
        if existing is None:
            raise KeyError(f"Document {doc_id} not found in {collection}")

        existing.update(updates)
        await self.set_document(collection, doc_id, existing)

    async def delete_document(self, collection: str, doc_id: str) -> None:
        """Delete a document."""
        await self._ensure_initialized()

        await self._conn.execute(
            "DELETE FROM collections WHERE collection_name = ? AND document_id = ?",
            (collection, doc_id),
        )
        await self._conn.execute(
            "DELETE FROM geo_index WHERE collection_name = ? AND document_id = ?",
            (collection, doc_id),
        )
        await self._conn.commit()

    async def list_documents(
        self, collection: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List all documents in a collection, optionally filtered."""
        await self._ensure_initialized()

        cursor = await self._conn.execute(
            "SELECT document_id, data FROM collections WHERE collection_name = ?",
            (collection,),
        )
        results = []
        async for row in cursor:
            data = json.loads(row["data"])
            data["id"] = row["document_id"]

            if filters:
                match = True
                for key, value in filters.items():
                    # Support nested keys like "location.ward_id"
                    keys = key.split(".")
                    val = data
                    for k in keys:
                        if isinstance(val, dict):
                            val = val.get(k)
                        else:
                            val = None
                            break
                    if val != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(data)

        return results

    # ------------------------------------------------------------------
    # Geo-radius query (replaces Firestore geo-query)
    # ------------------------------------------------------------------

    async def geo_radius_query(
        self,
        collection: str,
        lat: float,
        lng: float,
        radius_meters: float,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Find documents within a radius using bounding-box + haversine filter."""
        await self._ensure_initialized()

        dlat = _lat_delta(radius_meters)
        dlng = _lng_delta(radius_meters, lat)

        cursor = await self._conn.execute(
            """SELECT g.document_id, c.data
               FROM geo_index g
               JOIN collections c ON c.collection_name = g.collection_name
                                   AND c.document_id = g.document_id
               WHERE g.collection_name = ?
                 AND g.lat >= ? AND g.lat <= ?
                 AND g.lng >= ? AND g.lng <= ?""",
            (collection, lat - dlat, lat + dlat, lng - dlng, lng + dlng),
        )

        results = []
        async for row in cursor:
            data = json.loads(row["data"])
            data["id"] = row["document_id"]

            # Haversine filter
            doc_lat = data.get("lat") or data.get("location", {}).get("lat")
            doc_lng = data.get("lng") or data.get("location", {}).get("lng")
            if doc_lat is None or doc_lng is None:
                continue

            distance = _haversine_metres(lat, lng, float(doc_lat), float(doc_lng))
            if distance > radius_meters:
                continue

            # Apply additional filters
            if filters:
                match = True
                for key, value in filters.items():
                    keys = key.split(".")
                    val = data
                    for k in keys:
                        if isinstance(val, dict):
                            val = val.get(k)
                        else:
                            val = None
                            break
                    if val != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(data)

        return results

    # ------------------------------------------------------------------
    # RAG-specific helpers
    # ------------------------------------------------------------------

    async def save_document_chunks(
        self, doc_name: str, chunks: list[dict[str, Any]]
    ) -> None:
        """Save document chunks to the knowledge_base collection."""
        for chunk in chunks:
            chunk_id = f"{doc_name}_{chunk.get('chunk_index', 0)}"
            await self.set_document("knowledge_base", chunk_id, chunk)

    async def get_chunk_metadata(
        self, doc_name: str, chunk_idx: int
    ) -> dict[str, Any] | None:
        """Get metadata for a specific chunk."""
        chunk_id = f"{doc_name}_{chunk_idx}"
        return await self.get_document("knowledge_base", chunk_id)

    async def get_document_chunks(self, doc_name: str) -> list[dict[str, Any]]:
        """Get all chunks for a document."""
        return await self.list_documents(
            "knowledge_base", {"doc_name": doc_name}
        )

    async def delete_document_metadata(self, doc_name: str) -> None:
        """Delete all chunks for a document."""
        chunks = await self.get_document_chunks(doc_name)
        for chunk in chunks:
            chunk_id = chunk.get("id")
            if chunk_id:
                await self.delete_document("knowledge_base", chunk_id)

    # ------------------------------------------------------------------
    # Public - used by checkpointing
    # ------------------------------------------------------------------

    async def query_overdue_open_tasks(
        self, current_time_iso: str
    ) -> list[dict[str, Any]]:
        """Query tasks that are overdue."""
        await self._ensure_initialized()

        cursor = await self._conn.execute(
            """SELECT document_id, data FROM collections
               WHERE collection_name = 'tasks'
               ORDER BY updated_at DESC""",
        )

        results = []
        async for row in cursor:
            data = json.loads(row["data"])
            data["id"] = row["document_id"]

            if data.get("status") == "open":
                due_date = data.get("due_date", "")
                if due_date and due_date < current_time_iso:
                    results.append(data)

        return results

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Get a user profile."""
        return await self.get_document("users", user_id)

    async def get_assigned_officer(
        self, department: str
    ) -> dict[str, Any] | None:
        """Get the assigned officer for a department."""
        users = await self.list_documents("users", {"department": department})
        return users[0] if users else None

    async def log_notification(self, log_entry: dict[str, Any]) -> None:
        """Log a notification attempt."""
        import uuid
        await self.set_document(
            "notifications", f"notif_{uuid.uuid4().hex[:8]}", log_entry
        )

    async def read_community_health_score(self, ward_id: str) -> float | None:
        """Fetch the latest community health score for a ward."""
        scores = await self.list_documents(
            "community_scores", {"ward_id": ward_id}
        )
        if scores:
            return float(scores[-1].get("score", 0))
        return None
