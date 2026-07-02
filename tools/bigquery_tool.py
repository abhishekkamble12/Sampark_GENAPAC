"""
BigQuery tool for the Sampark AI Platform.

Provides async wrappers around the synchronous `google.cloud.bigquery` SDK,
running all blocking calls in a thread executor so they do not block the
asyncio event loop.

Usage:
    bq = BigQueryTool(project_id="my-gcp-project")
    rows = await bq.query_historical_issues("ward_5", "road", 90)
    ok   = await bq.write_predictions({...})
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google.cloud import bigquery

logger = logging.getLogger(__name__)


class BigQueryTool:
    """Async-friendly wrapper around the BigQuery client.

    Args:
        project_id: GCP project that owns the BigQuery dataset.
        dataset:    Dataset name.  Defaults to ``"sampark_analytics"``.
    """

    def __init__(self, project_id: str, dataset: str = "sampark_analytics") -> None:
        self._project_id = project_id
        self._dataset = dataset
        # Client is instantiated once and reused; the underlying HTTP
        # connections are thread-safe.
        self._client = bigquery.Client(project=project_id)

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def query_historical_issues(
        self,
        ward_id: str,
        issue_type: str,
        days: int,
    ) -> list[dict[str, Any]]:
        """Return historical issue rows matching the given filters.

        Runs a parameterised BigQuery query against the ``issues`` table and
        returns the results as a list of dicts (one dict per row).

        Args:
            ward_id:    Ward identifier to filter on.
            issue_type: Issue category to filter on (e.g. ``"road"``).
            days:       How many days back from now to look.

        Returns:
            List of row dicts, or an empty list on error.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                self._sync_query_historical_issues,
                ward_id,
                issue_type,
                days,
            )
        except Exception:
            logger.exception(
                "query_historical_issues failed for ward_id=%s issue_type=%s days=%d",
                ward_id,
                issue_type,
                days,
            )
            return []

    async def write_predictions(self, prediction_record: dict[str, Any]) -> bool:
        """Insert a single prediction record into the ``predictions`` table.

        Args:
            prediction_record: Dict whose keys correspond to the ``predictions``
                table schema fields.  A ``volume_forecast`` value that is a
                ``list`` will be JSON-serialised automatically before insertion.

        Returns:
            ``True`` on success, ``False`` on any error.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                self._sync_write_predictions,
                prediction_record,
            )
        except Exception:
            logger.exception(
                "write_predictions failed for prediction_record=%s",
                prediction_record,
            )
            return False

    # ------------------------------------------------------------------
    # Private synchronous helpers (run inside a thread executor)
    # ------------------------------------------------------------------

    def _sync_query_historical_issues(
        self,
        ward_id: str,
        issue_type: str,
        days: int,
    ) -> list[dict[str, Any]]:
        """Blocking implementation of :meth:`query_historical_issues`."""
        table = f"`{self._project_id}.{self._dataset}.issues`"

        sql = f"""
            SELECT *
            FROM   {table}
            WHERE  ward_id    = @ward_id
               AND type       = @issue_type
               AND reported_at >= TIMESTAMP_SUB(
                       CURRENT_TIMESTAMP(),
                       INTERVAL @days DAY
                   )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ward_id",    "STRING",  ward_id),
                bigquery.ScalarQueryParameter("issue_type", "STRING",  issue_type),
                bigquery.ScalarQueryParameter("days",       "INT64",   days),
            ]
        )

        query_job = self._client.query(sql, job_config=job_config)
        rows = query_job.result()  # blocks until the job is done

        return [dict(row) for row in rows]

    def _sync_write_predictions(
        self,
        prediction_record: dict[str, Any],
    ) -> bool:
        """Blocking implementation of :meth:`write_predictions`."""
        table_id = f"{self._project_id}.{self._dataset}.predictions"

        # The BigQuery ``predictions`` table stores ``volume_forecast`` as a
        # JSON STRING column.  If the caller passes a Python list/dict,
        # serialise it so the row insertion does not fail schema validation.
        row = dict(prediction_record)
        if isinstance(row.get("volume_forecast"), (list, dict)):
            row["volume_forecast"] = json.dumps(row["volume_forecast"])

        errors = self._client.insert_rows_json(table_id, [row])

        if errors:
            logger.error(
                "insert_rows_json returned errors for predictions table: %s",
                errors,
            )
            return False

        return True
