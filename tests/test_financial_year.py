"""Comprehensive unit test suite for Indian Financial Year & Month Skill.

Validates:
    - All 12 months forward conversion (Financial Month -> Calendar Month)
    - All 12 months reverse conversion (Calendar Month -> Financial Month)
    - Multiple financial years (FY 2024-25, FY 2025-26, FY 2026-27, FY 2027-28)
    - Quarters (Q1, Q2, Q3, Q4)
    - FY string parsing variations (FY2025-26, FY25-26, 2025-26, etc.)
    - Structured tool outputs (convert_financial_month, convert_calendar_to_financial, convert_financial_quarter)
    - Input validation and error handling for invalid months, years, and formats
"""

import pytest
from app.skills.financial_year import (
    calendar_to_financial_month,
    calendar_to_financial_year,
    convert_calendar_to_financial,
    convert_financial_month,
    convert_financial_quarter,
    financial_year_to_calendar_month,
    get_financial_quarter_months,
    parse_financial_month,
    parse_financial_year,
)


# ====================================================================
# 1. Forward Conversion Tests: Financial Month -> Calendar Month
# ====================================================================

def test_all_twelve_months_forward_conversion_fy2025_26():
    """Verify forward conversion for all 12 months of FY2025-26 (Oct-Sept)."""
    expected_mappings = [
        (1, "October 2025"),
        (2, "November 2025"),
        (3, "December 2025"),
        (4, "January 2026"),
        (5, "February 2026"),
        (6, "March 2026"),
        (7, "April 2026"),
        (8, "May 2026"),
        (9, "June 2026"),
        (10, "July 2026"),
        (11, "August 2026"),
        (12, "September 2026"),
    ]

    for fm, expected_str in expected_mappings:
        result = financial_year_to_calendar_month("FY2025-26", fm)
        assert result == expected_str, f"Expected FM {fm} of FY2025-26 to be '{expected_str}', got '{result}'"


def test_specific_prompt_forward_cases():
    """Verify specific forward conversion test cases required by prompt."""
    assert financial_year_to_calendar_month("FY2025-26", 1) == "October 2025"
    assert financial_year_to_calendar_month("FY2025-26", 4) == "January 2026"
    assert financial_year_to_calendar_month("FY2025-26", 7) == "April 2026"
    assert financial_year_to_calendar_month("FY2025-26", 10) == "July 2026"
    assert financial_year_to_calendar_month("FY2025-26", 12) == "September 2026"


# ====================================================================
# 2. Reverse Conversion Tests: Calendar Month -> Financial Month & FY
# ====================================================================

def test_all_twelve_months_reverse_conversion_fy2025_26():
    """Verify reverse conversion for all 12 calendar months covering FY2025-26."""
    calendar_to_fm_expected = [
        # (year, cal_month, expected_fy, expected_fm)
        (2025, 10, "FY2025-26", 1),  # October 2025
        (2025, 11, "FY2025-26", 2),  # November 2025
        (2025, 12, "FY2025-26", 3),  # December 2025
        (2026, 1, "FY2025-26", 4),   # January 2026
        (2026, 2, "FY2025-26", 5),   # February 2026
        (2026, 3, "FY2025-26", 6),   # March 2026
        (2026, 4, "FY2025-26", 7),   # April 2026
        (2026, 5, "FY2025-26", 8),   # May 2026
        (2026, 6, "FY2025-26", 9),   # June 2026
        (2026, 7, "FY2025-26", 10),  # July 2026
        (2026, 8, "FY2025-26", 11),  # August 2026
        (2026, 9, "FY2025-26", 12),  # September 2026
    ]

    for yr, cal_m, exp_fy, exp_fm in calendar_to_fm_expected:
        assert calendar_to_financial_year(yr, cal_m) == exp_fy
        assert calendar_to_financial_month(yr, cal_m) == exp_fm
        assert calendar_to_financial_month(cal_m) == exp_fm


def test_specific_prompt_reverse_cases():
    """Verify specific reverse conversion test cases required by prompt."""
    assert calendar_to_financial_year(2025, 10) == "FY2025-26"
    assert calendar_to_financial_year(2026, 9) == "FY2025-26"
    assert calendar_to_financial_month(2025, 10) == 1
    assert calendar_to_financial_month(2025, 12) == 3
    assert calendar_to_financial_month(2026, 1) == 4
    assert calendar_to_financial_month(2026, 9) == 12


# ====================================================================
# 3. Multiple Financial Years
# ====================================================================

@pytest.mark.parametrize(
    "fy_str, start_yr, end_yr",
    [
        ("FY2023-24", 2023, 2024),
        ("FY2024-25", 2024, 2025),
        ("FY2025-26", 2025, 2026),
        ("FY2026-27", 2026, 2027),
        ("FY2027-28", 2027, 2028),
    ],
)
def test_multiple_financial_years(fy_str, start_yr, end_yr):
    """Verify calculations work seamlessly across multiple past and future financial years."""
    # Month 1 is always October of start_year
    assert financial_year_to_calendar_month(fy_str, 1) == f"October {start_yr}"
    # Month 4 is always January of end_year
    assert financial_year_to_calendar_month(fy_str, 4) == f"January {end_yr}"
    # Month 12 is always September of end_year
    assert financial_year_to_calendar_month(fy_str, 12) == f"September {end_yr}"

    # Reverse
    assert calendar_to_financial_year(start_yr, 10) == fy_str
    assert calendar_to_financial_year(end_yr, 9) == fy_str


# ====================================================================
# 4. Notation Variations and Parsing
# ====================================================================

@pytest.mark.parametrize(
    "input_val, expected_start, expected_end, expected_str",
    [
        ("FY2025-26", 2025, 2026, "FY2025-26"),
        ("FY 2025-26", 2025, 2026, "FY2025-26"),
        ("FY2025-2026", 2025, 2026, "FY2025-26"),
        ("2025-26", 2025, 2026, "FY2025-26"),
        ("2025-2026", 2025, 2026, "FY2025-26"),
        ("FY25-26", 2025, 2026, "FY2025-26"),
        ("FY 25-26", 2025, 2026, "FY2025-26"),
        ("25-26", 2025, 2026, "FY2025-26"),
        ("2025-26 financial year", 2025, 2026, "FY2025-26"),
        ("financial year 2025-26", 2025, 2026, "FY2025-26"),
        ("financial year 2025", 2025, 2026, "FY2025-26"),
        ("FY2025", 2024, 2025, "FY2024-25"),
        (2025, 2025, 2026, "FY2025-26"),
    ],
)
def test_parse_financial_year_variations(input_val, expected_start, expected_end, expected_str):
    """Verify various string formats for financial year parse correctly."""
    s_yr, e_yr, canonical = parse_financial_year(input_val)
    assert s_yr == expected_start
    assert e_yr == expected_end
    assert canonical == expected_str


@pytest.mark.parametrize(
    "month_input, expected_fm",
    [
        (1, 1),
        (10, 10),
        ("1", 1),
        ("10", 10),
        ("month 10", 10),
        ("financial month 4", 4),
        ("FY month 12", 12),
        ("FM 6", 6),
        ("October", 1),
        ("January", 4),
        ("September", 12),
    ],
)
def test_parse_financial_month_variations(month_input, expected_fm):
    """Verify various inputs for financial month parse correctly."""
    assert parse_financial_month(month_input) == expected_fm


# ====================================================================
# 5. Financial Quarters Tests
# ====================================================================

def test_financial_quarters():
    """Verify financial quarter months mapping and conversion tool."""
    assert get_financial_quarter_months(1) == [1, 2, 3]
    assert get_financial_quarter_months("Q1") == [1, 2, 3]
    assert get_financial_quarter_months("Q2") == [4, 5, 6]
    assert get_financial_quarter_months("Q3") == [7, 8, 9]
    assert get_financial_quarter_months("Q4") == [10, 11, 12]

    q1_data = convert_financial_quarter("FY2025-26", "Q1")
    assert q1_data["financial_year"] == "FY2025-26"
    assert q1_data["quarter"] == "Q1"
    assert q1_data["financial_months"] == [1, 2, 3]
    assert q1_data["calendar_months"] == ["2025-10", "2025-11", "2025-12"]
    assert q1_data["calendar_month_names"] == ["October 2025", "November 2025", "December 2025"]

    q4_data = convert_financial_quarter("FY2025-26", "Q4")
    assert q4_data["financial_year"] == "FY2025-26"
    assert q4_data["quarter"] == "Q4"
    assert q4_data["financial_months"] == [10, 11, 12]
    assert q4_data["calendar_months"] == ["2026-07", "2026-08", "2026-09"]
    assert q4_data["calendar_month_names"] == ["July 2026", "August 2026", "September 2026"]


# ====================================================================
# 6. Structured Conversion Tools Output Tests
# ====================================================================

def test_convert_financial_month_tool_output():
    """Verify convert_financial_month tool produces exact structured dictionary."""
    result = convert_financial_month("FY2025-26", 4)
    assert result == {
        "financial_year": "FY2025-26",
        "financial_month": 4,
        "calendar_year": 2026,
        "calendar_month": 1,
        "calendar_month_name": "January",
        "calendar_date_month": "2026-01",
    }

    result_oct = convert_financial_month("FY2025-26", 1)
    assert result_oct == {
        "financial_year": "FY2025-26",
        "financial_month": 1,
        "calendar_year": 2025,
        "calendar_month": 10,
        "calendar_month_name": "October",
        "calendar_date_month": "2025-10",
    }


def test_convert_calendar_to_financial_tool_output():
    """Verify convert_calendar_to_financial tool output."""
    result = convert_calendar_to_financial(2026, 1)
    assert result == {
        "calendar_year": 2026,
        "calendar_month": 1,
        "calendar_month_name": "January",
        "financial_year": "FY2025-26",
        "financial_month": 4,
        "quarter": "Q2",
    }

    result_dec = convert_calendar_to_financial(2026, "December")
    assert result_dec == {
        "calendar_year": 2026,
        "calendar_month": 12,
        "calendar_month_name": "December",
        "financial_year": "FY2026-27",
        "financial_month": 3,
        "quarter": "Q1",
    }


# ====================================================================
# 7. Error Handling and Validation Tests
# ====================================================================

def test_validation_invalid_financial_months():
    """Verify invalid financial months raise ValueError."""
    with pytest.raises(ValueError):
        parse_financial_month(0)

    with pytest.raises(ValueError):
        parse_financial_month(13)

    with pytest.raises(ValueError):
        parse_financial_month(-5)

    with pytest.raises(ValueError):
        financial_year_to_calendar_month("FY2025-26", 0)

    with pytest.raises(ValueError):
        financial_year_to_calendar_month("FY2025-26", 13)

    with pytest.raises(ValueError):
        convert_financial_month("FY2025-26", "invalid")


def test_validation_invalid_financial_year():
    """Verify invalid financial year strings raise ValueError."""
    with pytest.raises(ValueError):
        parse_financial_year("")

    with pytest.raises(ValueError):
        parse_financial_year("   ")

    with pytest.raises(ValueError):
        parse_financial_year("FY2025-28")  # Non-consecutive years

    with pytest.raises(ValueError):
        parse_financial_year("invalid-format-xyz")


def test_validation_invalid_calendar_month():
    """Verify invalid calendar months raise ValueError."""
    with pytest.raises(ValueError):
        calendar_to_financial_month(0)

    with pytest.raises(ValueError):
        calendar_to_financial_month(13)

    with pytest.raises(ValueError):
        calendar_to_financial_year(2025, 0)

    with pytest.raises(ValueError):
        calendar_to_financial_year(2025, 13)

    with pytest.raises(ValueError):
        convert_calendar_to_financial(2025, "invalid-month")


def test_validation_invalid_quarter():
    """Verify invalid quarters raise ValueError."""
    with pytest.raises(ValueError):
        get_financial_quarter_months(0)

    with pytest.raises(ValueError):
        get_financial_quarter_months(5)

    with pytest.raises(ValueError):
        get_financial_quarter_months("Q5")

    with pytest.raises(ValueError):
        get_financial_quarter_months("invalid")
