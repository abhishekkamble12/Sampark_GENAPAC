"""
Firestore tool for the Sampark AI Platform.

Provides async CRUD operations, a geo-radius bounding-box query, and a
synchronous ``on_snapshot`` listener interface over the
``google.cloud.firestore_v1`` async client.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Callable

try:
    from google.cloud import firestore_v1
except ImportError:
    firestore_v1 = None

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


def _get_field_filter():
    if firestore_v1 is None:
        raise ImportError(
            "google-cloud-firestore is required for Firestore queries. "
            "Install it with: pip install google-cloud-firestore"
        )
    return firestore_v1.base_query.FieldFilter


class FirestoreTool:
    _local_db: dict[str, dict[str, dict[str, Any]]] = {}

    def __init__(self, db: Any) -> None:
        self._db = db

    async def geo_radius_query(
        self,
        collection: str,
        lat: float,
        lng: float,
        radius_meters: float,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self._db is None:
            results = []
            docs = self._local_db.get(collection, {})
            for doc_id, data in docs.items():
                match = True
                if filters:
                    for k, v in filters.items():
                        if data.get(k) != v:
                            match = False
                            break
                if not match:
                    continue
                doc_lat = data.get("lat") or data.get("location", {}).get("lat")
                doc_lng = data.get("lng") or data.get("location", {}).get("lng")
                if doc_lat is None or doc_lng is None:
                    continue
                distance = _haversine_metres(lat, lng, doc_lat, doc_lng)
                if distance <= radius_meters:
                    item = dict(data)
                    item["id"] = doc_id
                    item["lat"] = doc_lat
                    item["lng"] = doc_lng
                    results.append(item)
            return results

        try:
            dlat = _lat_delta(radius_meters)
            dlng = _lng_delta(radius_meters, lat)
            _FieldFilter = _get_field_filter()
            ref = self._db.collection(collection)
            query = ref
            if filters:
                for field, value in filters.items():
                    query = query.where(filter=_FieldFilter(field, "==", value))
            query = query.where(
                filter=_FieldFilter("lat", ">=", lat - dlat)
            ).where(
                filter=_FieldFilter("lat", "<=", lat + dlat)
            )
            results = []
            async for doc_snapshot in query.stream():
                data = doc_snapshot.to_dict() or {}
                doc_lng = data.get("lng")
                if doc_lng is None or not (lat - dlng <= data.get("lat", lat) <= lat + dlat):
                    pass
                if doc_lng is None or not (lng - dlng <= doc_lng <= lng + dlng):
                    continue
                doc_lat = data.get("lat")
                if doc_lat is None or doc_lng is None:
                    continue
                distance = _haversine_metres(lat, lng, doc_lat, doc_lng)
                if distance > radius_meters:
                    continue
                data["id"] = doc_snapshot.id
                results.append(data)
            return results
        except Exception:
            logger.exception(
                "geo_radius_query failed: collection=%s lat=%s lng=%s radius=%s",
                collection, lat, lng, radius_meters
            )
            return []

    async def get_document(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        if self._db is None:
            docs = self._local_db.get(collection, {})
            if doc_id in docs:
                data = dict(docs[doc_id])
                data["id"] = doc_id
                return data
            return None

        try:
            ref = self._db.collection(collection).document(doc_id)
            snapshot = await ref.get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            data["id"] = snapshot.id
            return data
        except Exception:
            logger.exception("get_document failed: collection=%s doc_id=%s", collection, doc_id)
            raise

    async def set_document(self, collection: str, doc_id: str, data: dict[str, Any], merge: bool = False) -> None:
        if self._db is None:
            if collection not in self._local_db:
                self._local_db[collection] = {}
            if merge and doc_id in self._local_db[collection]:
                self._local_db[collection][doc_id].update(data)
            else:
                self._local_db[collection][doc_id] = dict(data)
            return

        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.set(data, merge=merge)
        except Exception:
            logger.exception("set_document failed: collection=%s doc_id=%s merge=%s", collection, doc_id, merge)
            raise

    async def update_document(self, collection: str, doc_id: str, updates: dict[str, Any]) -> None:
        if self._db is None:
            if collection in self._local_db and doc_id in self._local_db[collection]:
                self._local_db[collection][doc_id].update(updates)
                return
            else:
                raise KeyError(f"Document {doc_id} not found in collection {collection}")

        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.update(updates)
        except Exception:
            logger.exception("update_document failed: collection=%s doc_id=%s", collection, doc_id)
            raise

    async def delete_document(self, collection: str, doc_id: str) -> None:
        if self._db is None:
            if collection in self._local_db and doc_id in self._local_db[collection]:
                del self._local_db[collection][doc_id]
            return

        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.delete()
        except Exception:
            logger.exception("delete_document failed: collection=%s doc_id=%s", collection, doc_id)
            raise

    def on_snapshot(self, collection: str, callback: Callable, filters: dict[str, Any] | None = None) -> Callable[[], None]:
        if self._db is None:
            return lambda: None

        ref = self._db.collection(collection)
        query = ref
        if filters:
            _FieldFilter = _get_field_filter()
            for field, value in filters.items():
                query = query.where(filter=_FieldFilter(field, "==", value))
        watch = query.on_snapshot(callback)
        def unsubscribe() -> None:
            try:
                watch.unsubscribe()
            except Exception:
                logger.exception("on_snapshot unsubscribe failed: collection=%s", collection)
        return unsubscribe

    async def save_document_chunks(self, doc_name: str, chunks: list[dict[str, Any]]) -> None:
        if self._db is None:
            for chunk in chunks:
                await self.set_document("knowledge_base", f"{doc_name}_{chunk['chunk_index']}", chunk)
            return

        batch = self._db.batch()
        for chunk in chunks:
            ref = self._db.collection("knowledge_base").document(f"{doc_name}_{chunk['chunk_index']}")
            batch.set(ref, chunk)
        await batch.commit()

    async def get_chunk_metadata(self, doc_name: str, chunk_idx: int) -> dict[str, Any] | None:
        if self._db is None:
            return await self.get_document("knowledge_base", f"{doc_name}_{chunk_idx}")

        ref = self._db.collection("knowledge_base").document(f"{doc_name}_{chunk_idx}")
        doc = await ref.get()
        return doc.to_dict() if doc.exists else None

    async def get_document_chunks(self, doc_name: str) -> list[dict[str, Any]]:
        if self._db is None:
            docs = self._local_db.get("knowledge_base", {})
            return [data for data in docs.values() if data.get("doc_name") == doc_name]

        _FieldFilter = _get_field_filter()
        docs = self._db.collection("knowledge_base").where(filter=_FieldFilter("doc_name", "==", doc_name)).stream()
        return [doc.to_dict() async for doc in docs]

    async def delete_document_metadata(self, doc_name: str) -> None:
        if self._db is None:
            docs = self._local_db.get("knowledge_base", {})
            to_delete = [doc_id for doc_id, data in docs.items() if data.get("doc_name") == doc_name]
            for doc_id in to_delete:
                del docs[doc_id]
            return

        _FieldFilter = _get_field_filter()
        docs = self._db.collection("knowledge_base").where(filter=_FieldFilter("doc_name", "==", doc_name)).stream()
        batch = self._db.batch()
        async for doc in docs:
            batch.delete(doc.reference)
        await batch.commit()
