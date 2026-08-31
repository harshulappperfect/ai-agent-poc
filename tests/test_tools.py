"""Automated test suite for Agentic AI Finance Toolset and Database Client.

Tests execute against the local PostgreSQL Docker container (finance-postgres).
"""

import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent / "plugins" / "finance-agent" / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import pytest
from tools import (  # type: ignore  # pyright: ignore[reportMissingImports]
    AVAILABLE_TOOLS,
    compare_forecast,
    convert_calendar_to_financial,
    convert_financial_month,
    convert_financial_quarter,
    get_database_schema,
    get_financial_data,
    get_org_summary,
    get_top_variances,
    run_read_only_query,
)


def test_get_financial_data_org_only():
    """Test retrieving all financial records for an organization."""
    records = get_financial_data("ORG001")
    assert isinstance(records, list)
    assert len(records) >= 6
    assert all(r["org_id"] == "ORG001" for r in records)
    assert all("forecast" in r and "actual" in r for r in records)


def test_get_financial_data_org_and_month():
    """Test retrieving financial record for a specific organization and month."""
    records = get_financial_data("ORG001", "2026-03")
    assert isinstance(records, list)
    assert len(records) >= 1
    rec = records[0]
    assert rec["org_id"] == "ORG001"
    assert "2026-03" in rec["month"]


def test_get_org_summary():
    """Test calculating aggregate summary for ORG003."""
    summary = get_org_summary("ORG003")
    assert isinstance(summary, dict)
    assert summary["org_id"] == "ORG003"
    assert summary["total_forecast"] > 0
    assert summary["total_actual"] > 0
    assert "variance" in summary
    assert "variance_percentage" in summary


def test_compare_forecast_single_month():
    """Test forecast comparison and performance classification for ORG005 in 2026-04."""
    comparisons = compare_forecast("ORG005", "2026-04")
    assert isinstance(comparisons, list)
    assert len(comparisons) >= 1
    comp = comparisons[0]
    assert comp["org_id"] == "ORG005"
    assert "2026-04" in comp["month"]
    assert comp["performance"] in ("above_forecast", "below_forecast", "on_forecast")


def test_compare_forecast_all_months():
    """Test forecast comparison across all months for an organization."""
    comparisons = compare_forecast("ORG001")
    assert isinstance(comparisons, list)
    assert len(comparisons) >= 6
    for comp in comparisons:
        assert comp["performance"] in ("above_forecast", "below_forecast", "on_forecast")


def test_get_top_variances():
    """Test retrieving top records ranked by absolute variance."""
    top_5 = get_top_variances(5)
    assert isinstance(top_5, list)
    assert len(top_5) == 5

    abs_variances = [abs(r["variance"]) for r in top_5]
    assert abs_variances == sorted(abs_variances, reverse=True)


def test_validation_invalid_org_id():
    """Test validation errors for invalid organization ID inputs."""
    with pytest.raises(ValueError):
        get_financial_data("")

    with pytest.raises(ValueError):
        get_financial_data("   ")

    with pytest.raises(ValueError):
        get_financial_data("ORG'; DROP TABLE financial_forecasts; --")


def test_validation_invalid_month():
    """Test validation errors for malformed month inputs."""
    with pytest.raises(ValueError):
        get_financial_data("ORG001", "invalid-month")

    with pytest.raises(ValueError):
        get_financial_data("ORG001", "2026-13")

    with pytest.raises(ValueError):
        get_financial_data("ORG001", "26-03")


def test_validation_invalid_limit():
    """Test validation errors for invalid limit inputs in get_top_variances."""
    with pytest.raises(ValueError):
        get_top_variances(0)

    with pytest.raises(ValueError):
        get_top_variances(-5)

    with pytest.raises(ValueError):
        get_top_variances(100)


def test_conversion_tools_in_available_tools():
    """Verify conversion tools are properly accessible in tools module."""
    assert "convert_financial_month" in AVAILABLE_TOOLS
    assert "convert_calendar_to_financial" in AVAILABLE_TOOLS
    assert "convert_financial_quarter" in AVAILABLE_TOOLS
    assert "get_database_schema" in AVAILABLE_TOOLS
    assert "run_read_only_query" in AVAILABLE_TOOLS

    res = convert_financial_month("FY2025-26", 4)
    assert res["calendar_date_month"] == "2026-01"

    records = get_financial_data("ORG001", res["calendar_date_month"])
    assert len(records) >= 1
    assert "2026-01" in records[0]["month"]


def test_get_database_schema():
    """Verify get_database_schema returns metadata for all 9 relational tables."""
    schema_info = get_database_schema()
    assert isinstance(schema_info, dict)
    assert schema_info["tables_count"] == 9
    expected_tables = {
        "budgets",
        "departments",
        "employees",
        "financial_forecasts",
        "invoices",
        "organizations",
        "projects",
        "transactions",
        "vendors",
    }
    assert expected_tables.issubset(set(schema_info["schema"].keys()))


def test_run_read_only_query_valid_select_and_cte():
    """Verify run_read_only_query executes valid SELECT and WITH (CTE) queries."""
    # Valid SELECT
    rows = run_read_only_query("SELECT id, org_id, forecast, actual FROM financial_forecasts ORDER BY id ASC LIMIT 2;")
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["org_id"] == "ORG001"

    # Valid WITH CTE
    cte_rows = run_read_only_query("WITH sub AS (SELECT * FROM financial_forecasts WHERE org_id = 'ORG001') SELECT * FROM sub LIMIT 3;")
    assert isinstance(cte_rows, list)
    assert len(cte_rows) == 3


def test_run_read_only_query_security_blocks_write():
    """Verify run_read_only_query blocks DML/DDL write queries."""
    with pytest.raises(ValueError, match="Security Error"):
        run_read_only_query("INSERT INTO financial_forecasts (org_id, month, forecast, actual) VALUES ('ORG999', '2026-01-01', 100, 100);")

    with pytest.raises(ValueError, match="Security Error"):
        run_read_only_query("DROP TABLE financial_forecasts;")

    with pytest.raises(ValueError, match="Security Error"):
        run_read_only_query("DELETE FROM financial_forecasts;")


