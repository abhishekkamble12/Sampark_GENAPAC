"""
Unit tests for tools/bigquery_tool.py

All Google Cloud SDK calls are mocked so these tests run without a real GCP
project or BigQuery instance.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tools.bigquery_tool import BigQueryTool


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

PROJECT = "test-project"
DATASET = "sampark_analytics"


def _make_tool(mock_client: MagicMock) -> BigQueryTool:
    """Create a BigQueryTool whose internal _client is replaced with a mock."""
    with patch("tools.bigquery_tool.bigquery.Client", return_value=mock_client):
        return BigQueryTool(project_id=PROJECT, dataset=DATASET)


def _fake_rows(data: list[dict]) -> list[MagicMock]:
    """Simulate BigQuery Row objects that support dict() conversion."""
    rows = []
    for d in data:
        row = MagicMock()
        row.keys.return_value = d.keys()
        row.__iter__ = lambda self, _d=d: iter(_d.items())
        # dict(row) calls row's __iter__ which yields (key, value) pairs
        rows.append(d)  # dict(row) for row in rows — rows are dicts here
    return rows


# ---------------------------------------------------------------------------
# query_historical_issues — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_historical_issues_returns_rows():
    """Successful query returns a non-empty list of dicts."""
    expected = [
        {"issue_id": "iss_1", "type": "road", "ward_id": "ward_5", "status": "open"},
        {"issue_id": "iss_2", "type": "road", "ward_id": "ward_5", "status": "resolved"},
    ]

    mock_client = MagicMock()
    # query_job.result() returns an iterable of BigQuery Row objects;
    # BigQueryTool does dict(row) on each — we use plain dicts here.
    mock_client.query.return_value.result.return_value = expected

    tool = _make_tool(mock_client)
    result = await tool.query_historical_issues("ward_5", "road", 90)

    assert result == expected


@pytest.mark.asyncio
async def test_query_historical_issues_uses_parameterised_query():
    """The SQL submitted to BigQuery must use named parameters, not literals."""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []

    tool = _make_tool(mock_client)
    await tool.query_historical_issues("ward_3", "flood", 30)

    # Extract the SQL string passed to client.query()
    call_args = mock_client.query.call_args
    sql: str = call_args[0][0]

    # Must use parameter placeholders — never string-interpolated values
    assert "@ward_id" in sql
    assert "@issue_type" in sql
    assert "@days" in sql
    # Must NOT embed raw values in the SQL
    assert "ward_3" not in sql
    assert "flood" not in sql
    assert "30" not in sql


@pytest.mark.asyncio
async def test_query_historical_issues_passes_correct_parameters():
    """Named query parameters are set with the correct names and values."""
    from google.cloud.bigquery import ScalarQueryParameter

    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []

    tool = _make_tool(mock_client)
    await tool.query_historical_issues("ward_7", "water", 60)

    job_config = mock_client.query.call_args[1]["job_config"]
    params: list[ScalarQueryParameter] = job_config.query_parameters

    param_map = {p.name: p.value for p in params}
    assert param_map["ward_id"] == "ward_7"
    assert param_map["issue_type"] == "water"
    assert param_map["days"] == 60


@pytest.mark.asyncio
async def test_query_historical_issues_returns_empty_list_on_client_error():
    """A BigQuery client exception is caught; the method returns an empty list."""
    mock_client = MagicMock()
    mock_client.query.side_effect = Exception("BQ unavailable")

    tool = _make_tool(mock_client)
    result = await tool.query_historical_issues("ward_1", "sanitation", 7)

    assert result == []


@pytest.mark.asyncio
async def test_query_historical_issues_returns_empty_list_when_no_rows():
    """Zero-row result is returned as an empty list (no error)."""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []

    tool = _make_tool(mock_client)
    result = await tool.query_historical_issues("ward_99", "other", 1)

    assert result == []


# ---------------------------------------------------------------------------
# write_predictions — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_predictions_returns_true_on_success():
    """insert_rows_json returning an empty errors list means success → True."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []  # no errors

    tool = _make_tool(mock_client)
    record: dict[str, Any] = {
        "prediction_id": "pred_001",
        "issue_id": "iss_abc",
        "ward_id": "ward_5",
        "flood_risk": 0.82,
        "road_risk": 0.45,
        "volume_forecast": [10, 12, 9, 11, 14, 8, 7],
        "computed_at": "2024-01-15T12:00:00Z",
    }

    result = await tool.write_predictions(record)
    assert result is True


@pytest.mark.asyncio
async def test_write_predictions_serialises_volume_forecast_list():
    """A list `volume_forecast` is JSON-serialised before being written to BQ."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    tool = _make_tool(mock_client)
    forecast = [10, 12, 9]
    await tool.write_predictions({"prediction_id": "p1", "volume_forecast": forecast})

    written_rows: list[dict] = mock_client.insert_rows_json.call_args[0][1]
    assert written_rows[0]["volume_forecast"] == json.dumps(forecast)


@pytest.mark.asyncio
async def test_write_predictions_does_not_re_serialise_string_forecast():
    """A string `volume_forecast` is passed through unchanged."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    tool = _make_tool(mock_client)
    serialised = json.dumps([1, 2, 3])
    await tool.write_predictions({"prediction_id": "p2", "volume_forecast": serialised})

    written_rows: list[dict] = mock_client.insert_rows_json.call_args[0][1]
    assert written_rows[0]["volume_forecast"] == serialised


@pytest.mark.asyncio
async def test_write_predictions_returns_false_on_insert_errors():
    """insert_rows_json returning errors means failure → False."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = [
        {"index": 0, "errors": [{"reason": "invalid", "message": "bad value"}]}
    ]

    tool = _make_tool(mock_client)
    result = await tool.write_predictions({"prediction_id": "p3"})

    assert result is False


@pytest.mark.asyncio
async def test_write_predictions_returns_false_on_client_exception():
    """A client exception is caught; the method returns False."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.side_effect = Exception("network error")

    tool = _make_tool(mock_client)
    result = await tool.write_predictions({"prediction_id": "p4"})

    assert result is False


@pytest.mark.asyncio
async def test_write_predictions_inserts_into_correct_table():
    """The fully-qualified predictions table ID is used for insertion."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    tool = _make_tool(mock_client)
    await tool.write_predictions({"prediction_id": "p5"})

    table_arg: str = mock_client.insert_rows_json.call_args[0][0]
    assert table_arg == f"{PROJECT}.{DATASET}.predictions"


@pytest.mark.asyncio
async def test_write_predictions_does_not_mutate_original_record():
    """The original dict passed by the caller is never modified in-place."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    tool = _make_tool(mock_client)
    original_forecast = [5, 6, 7]
    record = {"prediction_id": "p6", "volume_forecast": original_forecast}

    await tool.write_predictions(record)

    # The original list should still be a list, not a JSON string
    assert record["volume_forecast"] is original_forecast


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_sets_project_and_dataset():
    """Project ID and dataset name are stored as instance attributes."""
    mock_client = MagicMock()
    with patch("tools.bigquery_tool.bigquery.Client", return_value=mock_client):
        tool = BigQueryTool(project_id="proj-x", dataset="custom_ds")

    assert tool._project_id == "proj-x"
    assert tool._dataset == "custom_ds"


def test_constructor_default_dataset():
    """Default dataset is ``sampark_analytics``."""
    mock_client = MagicMock()
    with patch("tools.bigquery_tool.bigquery.Client", return_value=mock_client):
        tool = BigQueryTool(project_id="proj-y")

    assert tool._dataset == "sampark_analytics"
