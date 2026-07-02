"""
Firestore tool for the Sampark AI Platform.

Provides async CRUD operations, a geo-radius bounding-box query, and a
synchronous ``on_snapshot`` listener interface over the
``google.cloud.firestore_v1`` async client.

Usage::

    from google.cloud import firestore
    db = firestore.AsyncClient(project="my-gcp-project")
    fs = FirestoreTool(db)

    # Geo-radius query
    nearby = await fs.geo_radius_query("issues", lat=18.52, lng=73.86,
                                        radius_meters=500,
                                        filters={"type": "road"})

    # CRUD
    doc = await fs.get_document("issues", "iss_abc")
    await fs.set_document("issues", "iss_xyz", {"type": "flood"})
    await fs.update_document("tasks", "task_001", {"status": "in_progress"})
    await fs.delete_document("issues", "iss_old")

    # Real-time listener
    unsubscribe = fs.on_snapshot("tasks", callback=my_callback,
                                  filters={"status": "open"})
    # ... later ...
    unsubscribe()
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any, Callable

# google-cloud-firestore is an optional dependency at import time so that the
# module can be loaded (and mocked) in test environments without the SDK
# installed.  The try/except guard exposes a sentinel type for the constructor
# annotation when the real SDK is absent.
try:
    from google.cloud import firestore_v1  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    firestore_v1 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------

# At the equator, 1 degree of latitude is approximately 111,320 metres.
_METRES_PER_LAT_DEGREE: float = 111_320.0


def _lat_delta(radius_metres: float) -> float:
    """Return the latitude delta (degrees) that covers *radius_metres*."""
    return radius_metres / _METRES_PER_LAT_DEGREE


def _lng_delta(radius_metres: float, lat: float) -> float:
    """Return the longitude delta (degrees) that covers *radius_metres* at *lat*."""
    # 1 degree of longitude shrinks as cos(lat) at higher latitudes.
    cos_lat = math.cos(math.radians(lat))
    if cos_lat < 1e-9:
        # Avoid division by zero at the poles — return a very wide bound.
        return 180.0
    return radius_metres / (_METRES_PER_LAT_DEGREE * cos_lat)


def _haversine_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in metres between two coordinates."""
    r = 6_371_000.0  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_field_filter():
    """Return ``google.cloud.firestore_v1.base_query.FieldFilter``.

    Resolved lazily so the module can be imported without the SDK installed.
    """
    if firestore_v1 is None:  # pragma: no cover
        raise ImportError(
            "google-cloud-firestore is required for Firestore queries. "
            "Install it with: pip install google-cloud-firestore"
        )
    return firestore_v1.base_query.FieldFilter


class FirestoreTool:
    """Async-friendly Firestore wrapper with geo-query and listener support.

    Args:
        db: An initialised :class:`google.cloud.firestore_v1.AsyncClient`.
    """

    def __init__(self, db: firestore_v1.AsyncClient) -> None:
        self._db = db

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
        """Return documents within *radius_meters* of (lat, lng).

        Firestore does not support native geo-range queries, so this method
        applies a bounding-box pre-filter on ``lat`` and ``lng`` fields to
        reduce the candidate set, then refines the results using the exact
        Haversine distance.  Documents must store their coordinates as
        top-level numeric fields named ``lat`` and ``lng``.

        Optional *filters* are applied as equality conditions **before** the
        bounding-box filter.

        Args:
            collection:     Firestore collection path.
            lat:            Centre latitude in decimal degrees.
            lng:            Centre longitude in decimal degrees.
            radius_meters:  Search radius in metres.
            filters:        Optional dict of ``{field: value}`` equality
                            filters applied to the query.

        Returns:
            List of document dicts (each includes an ``"id"`` key set to the
            Firestore document ID).  Returns an empty list on any error.
        """
        try:
            dlat = _lat_delta(radius_meters)
            dlng = _lng_delta(radius_meters, lat)

            # Resolve FieldFilter lazily so the module loads even when the
            # Firestore SDK is not installed (e.g. in unit-test environments).
            _FieldFilter = _get_field_filter()

            ref = self._db.collection(collection)

            # Build the query: optional equality filters + bounding-box range
            query = ref

            if filters:
                for field, value in filters.items():
                    query = query.where(filter=_FieldFilter(field, "==", value))

            # Bounding-box on lat only (Firestore allows range filter on one
            # field at a time; applying lng range would require a composite
            # index that may not exist).  Lng is filtered in Python below.
            query = query.where(
                filter=_FieldFilter("lat", ">=", lat - dlat)
            ).where(
                filter=_FieldFilter("lat", "<=", lat + dlat)
            )

            results: list[dict[str, Any]] = []
            async for doc_snapshot in query.stream():
                data = doc_snapshot.to_dict() or {}

                # Longitude bounding-box check (in Python)
                doc_lng = data.get("lng")
                if doc_lng is None or not (lat - dlng <= data.get("lat", lat) <= lat + dlat):
                    # lat already filtered above; check lng here
                    pass
                if doc_lng is None or not (lng - dlng <= doc_lng <= lng + dlng):
                    continue

                # Exact Haversine filter
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
                collection,
                lat,
                lng,
                radius_meters,
            )
            return []

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------

    async def get_document(
        self,
        collection: str,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single document by ID.

        Args:
            collection: Firestore collection path.
            doc_id:     Document identifier.

        Returns:
            Document data dict (including ``"id"`` key) or ``None`` if the
            document does not exist.

        Raises:
            google.cloud.exceptions.GoogleCloudError: On Firestore API errors.
        """
        try:
            ref = self._db.collection(collection).document(doc_id)
            snapshot = await ref.get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            data["id"] = snapshot.id
            return data
        except Exception:
            logger.exception(
                "get_document failed: collection=%s doc_id=%s", collection, doc_id
            )
            raise

    async def set_document(
        self,
        collection: str,
        doc_id: str,
        data: dict[str, Any],
        merge: bool = False,
    ) -> None:
        """Create or overwrite a document.

        Args:
            collection: Firestore collection path.
            doc_id:     Document identifier.
            data:       Fields to write.
            merge:      If ``True``, merge *data* into the existing document
                        rather than overwriting it entirely.

        Raises:
            google.cloud.exceptions.GoogleCloudError: On Firestore API errors.
        """
        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.set(data, merge=merge)
        except Exception:
            logger.exception(
                "set_document failed: collection=%s doc_id=%s merge=%s",
                collection,
                doc_id,
                merge,
            )
            raise

    async def update_document(
        self,
        collection: str,
        doc_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Partially update an existing document.

        Only the fields present in *updates* are modified; all other fields
        remain untouched.

        Args:
            collection: Firestore collection path.
            doc_id:     Document identifier.
            updates:    Field-value pairs to update.

        Raises:
            google.cloud.exceptions.GoogleCloudError: On Firestore API errors
                or if the document does not exist.
        """
        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.update(updates)
        except Exception:
            logger.exception(
                "update_document failed: collection=%s doc_id=%s", collection, doc_id
            )
            raise

    async def delete_document(
        self,
        collection: str,
        doc_id: str,
    ) -> None:
        """Delete a document.

        Deleting a non-existent document is a no-op and does **not** raise.

        Args:
            collection: Firestore collection path.
            doc_id:     Document identifier.

        Raises:
            google.cloud.exceptions.GoogleCloudError: On Firestore API errors.
        """
        try:
            ref = self._db.collection(collection).document(doc_id)
            await ref.delete()
        except Exception:
            logger.exception(
                "delete_document failed: collection=%s doc_id=%s", collection, doc_id
            )
            raise

    # ------------------------------------------------------------------
    # Real-time listener
    # ------------------------------------------------------------------

    def on_snapshot(
        self,
        collection: str,
        callback: Callable,
        filters: dict[str, Any] | None = None,
    ) -> Callable[[], None]:
        """Register an ``on_snapshot`` listener on a collection query.

        The listener is attached synchronously.  Firestore will call
        *callback* with ``(collection_snapshot, changes, read_time)``
        whenever a matching document changes.

        Equality *filters* narrow the subscription to documents whose field
        values match the provided dict.

        Args:
            collection: Firestore collection path.
            callback:   Callable invoked by Firestore on each snapshot event.
                        Signature: ``callback(docs, changes, read_time)``.
            filters:    Optional dict of ``{field: value}`` equality filters.

        Returns:
            An *unsubscribe* callable.  Call it (no arguments) to detach the
            listener and free the underlying watch.

        Raises:
            google.cloud.exceptions.GoogleCloudError: If the listener cannot
                be established (e.g. permission denied).
        """
        ref = self._db.collection(collection)
        query = ref

        if filters:
            _FieldFilter = _get_field_filter()
            for field, value in filters.items():
                query = query.where(
                    filter=_FieldFilter(field, "==", value)
                )

        # ``on_snapshot`` is available on both collection references and
        # query objects and returns a ``Watch`` whose ``unsubscribe`` method
        # detaches the listener.
        watch = query.on_snapshot(callback)

        def unsubscribe() -> None:
            """Detach the Firestore listener."""
            try:
                watch.unsubscribe()
            except Exception:
                logger.exception(
                    "on_snapshot unsubscribe failed: collection=%s", collection
                )

        return unsubscribe
