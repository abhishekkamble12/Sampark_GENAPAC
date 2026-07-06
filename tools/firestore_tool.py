"""
tools/firestore_tool.py — Database Tool Adapter (FREE replacement for Firestore)

Delegates all operations to tools.sqlite_tool.DatabaseTool for local
SQLite storage. Maintains the same interface for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Local in-memory fallback (same as old FirestoreTool._local_db)
_local_db: dict[str, dict[str, dict[str, Any]]] = {}


class FirestoreTool:
    """Adapter that provides the same interface as the old FirestoreTool.

    In local mode, uses an in-memory dict (backward compatible with tests).
    When a DatabaseTool instance is provided, delegates to SQLite.
    """

    _local_db: dict[str, dict[str, dict[str, Any]]] = _local_db
    _sqlite_db: Any = None  # DatabaseTool instance, if available

    def __init__(self, db: Any = None) -> None:
        """Initialize with optional SQLite DatabaseTool.

        Args:
            db: DatabaseTool instance or None (uses in-memory fallback)
        """
        if db is not None and hasattr(db, "set_document"):
            FirestoreTool._sqlite_db = db
        else:
            FirestoreTool._sqlite_db = None

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------

    async def set_document(
        self, collection: str, doc_id: str, data: dict[str, Any], merge: bool = False
    ) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.set_document(collection, doc_id, data, merge=merge)
            return

        if collection not in _local_db:
            _local_db[collection] = {}
        if merge and doc_id in _local_db[collection]:
            _local_db[collection][doc_id].update(data)
        else:
            _local_db[collection][doc_id] = dict(data)

    async def get_document(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.get_document(collection, doc_id)

        docs = _local_db.get(collection, {})
        if doc_id in docs:
            data = dict(docs[doc_id])
            data["id"] = doc_id
            return data
        return None

    async def update_document(self, collection: str, doc_id: str, updates: dict[str, Any]) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.update_document(collection, doc_id, updates)
            return

        if collection in _local_db and doc_id in _local_db[collection]:
            _local_db[collection][doc_id].update(updates)
        else:
            raise KeyError(f"Document {doc_id} not found in collection {collection}")

    async def delete_document(self, collection: str, doc_id: str) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.delete_document(collection, doc_id)
            return

        if collection in _local_db and doc_id in _local_db[collection]:
            del _local_db[collection][doc_id]

    async def list_documents(self, collection: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.list_documents(collection, filters)

        results = []
        for doc_id, data in _local_db.get(collection, {}).items():
            if filters:
                match = True
                for k, v in filters.items():
                    keys = k.split(".")
                    val = data
                    for key in keys:
                        val = val.get(key) if isinstance(val, dict) else None
                    if val != v:
                        match = False
                        break
                if not match:
                    continue
            item = dict(data)
            item["id"] = doc_id
            results.append(item)
        return results

    # ------------------------------------------------------------------
    # Geo-radius query
    # ------------------------------------------------------------------

    async def geo_radius_query(
        self,
        collection: str,
        lat: float,
        lng: float,
        radius_meters: float,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.geo_radius_query(
                collection, lat, lng, radius_meters, filters
            )

        # In-memory fallback
        import math
        results = []
        docs = _local_db.get(collection, {})
        for doc_id, data in docs.items():
            match = True
            if filters:
                for k, v in filters.items():
                    keys = k.split(".")
                    val = data
                    for key in keys:
                        val = val.get(key) if isinstance(val, dict) else None
                    if val != v:
                        match = False
                        break
            if not match:
                continue
            doc_lat = data.get("lat") or data.get("location", {}).get("lat")
            doc_lng = data.get("lng") or data.get("location", {}).get("lng")
            if doc_lat is None or doc_lng is None:
                continue
            # Haversine
            r = 6_371_000.0
            phi1 = math.radians(lat)
            phi2 = math.radians(float(doc_lat))
            d_phi = math.radians(float(doc_lat) - lat)
            d_lambda = math.radians(float(doc_lng) - lng)
            a = (math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
            distance = r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if distance <= radius_meters:
                item = dict(data)
                item["id"] = doc_id
                results.append(item)
        return results

    # ------------------------------------------------------------------
    # RAG helpers
    # ------------------------------------------------------------------

    async def save_document_chunks(self, doc_name: str, chunks: list[dict[str, Any]]) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.save_document_chunks(doc_name, chunks)
            return
        for chunk in chunks:
            await self.set_document("knowledge_base", f"{doc_name}_{chunk['chunk_index']}", chunk)

    async def get_chunk_metadata(self, doc_name: str, chunk_idx: int) -> dict[str, Any] | None:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.get_chunk_metadata(doc_name, chunk_idx)
        return await self.get_document("knowledge_base", f"{doc_name}_{chunk_idx}")

    async def get_document_chunks(self, doc_name: str) -> list[dict[str, Any]]:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.get_document_chunks(doc_name)
        docs = _local_db.get("knowledge_base", {})
        return [data for data in docs.values() if data.get("doc_name") == doc_name]

    async def delete_document_metadata(self, doc_name: str) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.delete_document_metadata(doc_name)
            return
        docs = _local_db.get("knowledge_base", {})
        to_delete = [doc_id for doc_id, data in docs.items() if data.get("doc_name") == doc_name]
        for doc_id in to_delete:
            del docs[doc_id]

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------

    async def query_overdue_open_tasks(self, current_time_iso: str) -> list[dict[str, Any]]:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.query_overdue_open_tasks(current_time_iso)
        tasks = _local_db.get("tasks", {})
        return [t for t in tasks.values() if t.get("status") == "open" and t.get("due_date", "") < current_time_iso]

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.get_user_profile(user_id)
        return await self.get_document("users", user_id)

    async def get_assigned_officer(self, department: str) -> dict[str, Any] | None:
        if FirestoreTool._sqlite_db:
            return await FirestoreTool._sqlite_db.get_assigned_officer(department)
        users = await self.list_documents("users", {"department": department})
        return users[0] if users else None

    async def log_notification(self, log_entry: dict[str, Any]) -> None:
        if FirestoreTool._sqlite_db:
            await FirestoreTool._sqlite_db.log_notification(log_entry)
            return
        import uuid
        await self.set_document("notifications", f"notif_{uuid.uuid4().hex[:8]}", log_entry)

    # ------------------------------------------------------------------
    # Snapshot listener (mock — no-op in free stack)
    # ------------------------------------------------------------------

    def on_snapshot(self, collection: str, callback: Callable, filters: dict[str, Any] | None = None) -> Callable[[], None]:
        return lambda: None
