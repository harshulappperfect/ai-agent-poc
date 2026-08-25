"""Automated test suite for Agentic AI Finance Toolset and Database Client.

Tests execute against the local PostgreSQL Docker container (finance-postgres).
"""

import pytest
from app.tools import (
    compare_forecast,
    get_financial_data,
    get_org_summary,
    get_top_variances,
)


def test_get_financial_data_org_only():
    """Test retrieving all financial records for an organization."""
    records = get_financial_data("ORG001")
    assert isinstance(records, list)
    assert len(records) == 6
    assert all(r["org_id"] == "ORG001" for r in records)
    assert all("forecast" in r and "actual" in r for r in records)


def test_get_financial_data_org_and_month():
    """Test retrieving financial record for a specific organization and month."""
    records = get_financial_data("ORG001", "2026-03")
    assert isinstance(records, list)
    assert len(records) == 1
    rec = records[0]
    assert rec["id"] == 3
    assert rec["org_id"] == "ORG001"
    assert rec["month"] == "2026-03-01"
    assert rec["forecast"] == 110000.0
    assert rec["actual"] == 107500.0


def test_get_org_summary():
    """Test calculating aggregate summary, variance, and percentage for ORG003."""
    summary = get_org_summary("ORG003")
    assert isinstance(summary, dict)
    assert summary["org_id"] == "ORG003"
    # ORG003: Forecast sum = 150k+155k+160k+165k+170k+175k = 975000
    # Actual sum = 148k+160k+158.5k+170k+168k+179.5k = 984000
    # Variance = +9000
    # Variance % = (9000 / 975000) * 100 = 0.92%
    assert summary["total_forecast"] == 975000.0
    assert summary["total_actual"] == 984000.0
    assert summary["variance"] == 9000.0
    assert summary["variance_percentage"] == 0.92


def test_compare_forecast_single_month():
    """Test forecast comparison and performance classification for ORG005 in 2026-04."""
    comparisons = compare_forecast("ORG005", "2026-04")
    assert isinstance(comparisons, list)
    assert len(comparisons) == 1
    comp = comparisons[0]
    assert comp["org_id"] == "ORG005"
    assert comp["month"] == "2026-04-01"
    assert comp["forecast"] == 230000.0
    assert comp["actual"] == 235000.0
    assert comp["variance"] == 5000.0
    assert comp["variance_percentage"] == 2.17
    assert comp["performance"] == "above_forecast"


def test_compare_forecast_all_months():
    """Test forecast comparison across all months for an organization."""
    comparisons = compare_forecast("ORG001")
    assert isinstance(comparisons, list)
    assert len(comparisons) == 6
    # Check that performance classification is always valid
    for comp in comparisons:
        assert comp["performance"] in ("above_forecast", "below_forecast", "on_forecast")
        if comp["actual"] > comp["forecast"]:
            assert comp["performance"] == "above_forecast"
        elif comp["actual"] < comp["forecast"]:
            assert comp["performance"] == "below_forecast"
        else:
            assert comp["performance"] == "on_forecast"


def test_get_top_variances():
    """Test retrieving top records ranked by absolute variance."""
    top_5 = get_top_variances(5)
    assert isinstance(top_5, list)
    assert len(top_5) == 5

    # Verify that variances are sorted by absolute value descending
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
        get_top_variances(100)  # Exceeds max allowed limit of 50


def test_conversion_tools_in_available_tools():
    """Verify conversion tools are properly accessible in app.tools."""
    from app.tools import (
        AVAILABLE_TOOLS,
        convert_calendar_to_financial,
        convert_financial_month,
        convert_financial_quarter,
    )
    assert "convert_financial_month" in AVAILABLE_TOOLS
    assert "convert_calendar_to_financial" in AVAILABLE_TOOLS
    assert "convert_financial_quarter" in AVAILABLE_TOOLS

    # Test invoking convert_financial_month via tools module
    res = convert_financial_month("FY2025-26", 10)
    assert res["calendar_date_month"] == "2026-01"

    # Test end-to-end chaining: convert FY month 10 -> pass to get_financial_data
    records = get_financial_data("ORG001", res["calendar_date_month"])
    assert len(records) == 1
    assert records[0]["month"] == "2026-01-01"
    assert records[0]["actual"] == 98000.0

