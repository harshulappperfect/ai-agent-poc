"""Deterministic Indian Financial Year (FY) and Month Conversion Logic.

Financial Year Convention:
    - Runs from October 1 through September 30.
    - FY Month 1  = October
    - FY Month 2  = November
    - FY Month 3  = December
    - FY Month 4  = January (following calendar year)
    - FY Month 5  = February (following calendar year)
    - FY Month 6  = March (following calendar year)
    - FY Month 7  = April (following calendar year)
    - FY Month 8  = May (following calendar year)
    - FY Month 9  = June (following calendar year)
    - FY Month 10 = July (following calendar year)
    - FY Month 11 = August (following calendar year)
    - FY Month 12 = September (following calendar year)

Quarters:
    - Q1 = Months 1 to 3  (October to December)
    - Q2 = Months 4 to 6  (January to March)
    - Q3 = Months 7 to 9  (April to June)
    - Q4 = Months 10 to 12 (July to September)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import re
from typing import Any

# Calendar month name mappings (1-indexed)
CALENDAR_MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

# Reverse lookup for month names (lowercase -> month int)
MONTH_NAME_TO_INT = {name.lower(): num for num, name in CALENDAR_MONTH_NAMES.items()}
MONTH_NAME_TO_INT.update({
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
})

# Quarter mappings
QUARTER_TO_FY_MONTHS = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}


def parse_financial_year(financial_year_input: str | int) -> tuple[int, int, str]:
    """Parse and validate a financial year input into start year, end year, and canonical string.
    
    Supports:
        - "FY2025-26", "FY 2025-26", "FY2025-2026", "FY 2025-2026"
        - "FY25-26", "FY 25-26", "25-26"
        - "2025-26", "2025-2026"
        - "2025-26 financial year", "financial year 2025-26", "fiscal year 2025-26"
        - "financial year 2025", "FY2025", 2025
        - "FY2026", "FY26" (interpreted as FY ending in 2026, i.e. FY2025-26)
        
    Args:
        financial_year_input: Raw string or integer representation of FY.
        
    Returns:
        tuple[int, int, str]: (start_year, end_year, "FY{start_year}-{end_year_short}")
        
    Raises:
        ValueError: If financial_year_input cannot be parsed or is invalid.
    """
    if isinstance(financial_year_input, int):
        start_year = financial_year_input
        end_year = start_year + 1
        return start_year, end_year, f"FY{start_year}-{str(end_year)[-2:]}"

    if not isinstance(financial_year_input, str) or not financial_year_input.strip():
        raise ValueError("Financial year must be a non-empty string or integer (e.g., 'FY2025-26').")

    cleaned = financial_year_input.strip()

    # Match 4-digit start and 2-digit/4-digit end year: e.g. FY2025-26, 2025-2026, FY 2025-26
    match_full = re.search(r"(?:FY|FINANCIAL\s*YEAR|FISCAL\s*YEAR)?\s*(\d{4})\s*[-/]\s*(\d{2,4})", cleaned, re.IGNORECASE)
    if match_full:
        start_yr = int(match_full.group(1))
        end_yr_str = match_full.group(2)
        if len(end_yr_str) == 2:
            # Century reconstruction (e.g. 2025 and 26 -> 2026)
            century = (start_yr // 100) * 100
            end_yr = century + int(end_yr_str)
            if end_yr < start_yr:
                end_yr += 100
        else:
            end_yr = int(end_yr_str)

        if end_yr != start_yr + 1:
            raise ValueError(f"Invalid financial year span: '{financial_year_input}'. End year must be start year + 1.")

        return start_yr, end_yr, f"FY{start_yr}-{str(end_yr)[-2:]}"

    # Match 2-digit start and 2-digit end year: e.g. FY25-26, 25-26
    match_short = re.search(r"(?:FY|FINANCIAL\s*YEAR|FISCAL\s*YEAR)?\s*(\d{2})\s*[-/]\s*(\d{2})", cleaned, re.IGNORECASE)
    if match_short:
        start_2d = int(match_short.group(1))
        end_2d = int(match_short.group(2))
        start_yr = 2000 + start_2d if start_2d < 70 else 1900 + start_2d
        end_yr = 2000 + end_2d if end_2d < 70 else 1900 + end_2d

        if end_yr != start_yr + 1:
            raise ValueError(f"Invalid financial year span: '{financial_year_input}'. End year must be start year + 1.")

        return start_yr, end_yr, f"FY{start_yr}-{str(end_yr)[-2:]}"

    # Match standalone 4-digit year: e.g. "financial year 2025", "FY2025", "2025"
    match_single_4d = re.search(r"(\d{4})", cleaned)
    if match_single_4d:
        yr = int(match_single_4d.group(1))
        # If explicitly formatted as FY2026 (single ending year commonly used in reports)
        if re.search(r"FY\s*\d{4}", cleaned, re.IGNORECASE) and not re.search(r"START|BEGIN", cleaned, re.IGNORECASE):
            # Check if user meant FY2025-26 (ending 2026) or starting 2026.
            # In Indian convention FY26 is the year ending March 2026.
            start_yr = yr - 1
            end_yr = yr
        else:
            start_yr = yr
            end_yr = yr + 1
        return start_yr, end_yr, f"FY{start_yr}-{str(end_yr)[-2:]}"

    raise ValueError(f"Invalid financial year format: '{financial_year_input}'. Expected formats like 'FY2025-26' or '2025-26'.")


def parse_financial_month(financial_month_input: str | int) -> int:
    """Parse and validate a financial month input (1 to 12).
    
    Supports:
        - Integers: 1 to 12
        - Strings: "1" to "12"
        - Strings with labels: "month 10", "financial month 4", "FY month 1"
        - Calendar month names: "April" -> 1, "January" -> 10, etc.
        
    Args:
        financial_month_input: Raw financial month representation.
        
    Returns:
        int: Validated financial month (1 to 12).
        
    Raises:
        ValueError: If financial_month_input is outside 1-12 or cannot be parsed.
    """
    if isinstance(financial_month_input, int):
        if not (1 <= financial_month_input <= 12):
            raise ValueError(f"Invalid financial month: {financial_month_input}. Financial month must be between 1 and 12.")
        return financial_month_input

    if not isinstance(financial_month_input, str) or not financial_month_input.strip():
        raise ValueError("Financial month must be a non-empty string or integer (1-12).")

    cleaned = financial_month_input.strip()

    # Check for direct integer in string
    match_num = re.search(r"(?:MONTH|FY\s*MONTH|FINANCIAL\s*MONTH|FM)?\s*(\d+)", cleaned, re.IGNORECASE)
    if match_num and match_num.group(1):
        m_val = int(match_num.group(1))
        if not (1 <= m_val <= 12):
            raise ValueError(f"Invalid financial month: {m_val}. Financial month must be between 1 and 12.")
        return m_val

    # Check if a calendar month name was supplied directly
    cleaned_lower = cleaned.lower()
    for name, num in MONTH_NAME_TO_INT.items():
        if name in cleaned_lower:
            # Map calendar month to FY month
            return calendar_to_financial_month(num)

    raise ValueError(f"Invalid financial month format: '{financial_month_input}'. Expected 1-12 or month name.")


def calendar_to_financial_year(year: int, month: int) -> str:
    """Convert a calendar year and month to the corresponding Indian Financial Year string.
    
    Args:
        year: Calendar year (e.g., 2025).
        month: Calendar month (1 to 12, where 1=Jan, 4=Apr, etc.).
        
    Returns:
        str: Canonical financial year string (e.g., "FY2025-26").
        
    Raises:
        ValueError: If month is not between 1 and 12, or year is invalid.
    """
    if not isinstance(month, int) or not (1 <= month <= 12):
        raise ValueError(f"Invalid calendar month: {month}. Month must be an integer between 1 and 12.")
    if not isinstance(year, int) or year < 1000 or year > 9999:
        raise ValueError(f"Invalid calendar year: {year}. Year must be a 4-digit integer.")

    if month >= 10:
        start_year = year
    else:
        start_year = year - 1

    end_year = start_year + 1
    return f"FY{start_year}-{str(end_year)[-2:]}"


def calendar_to_financial_month(year_or_month: int, month: int | None = None) -> int:
    """Convert a calendar month to its corresponding Indian Financial Month number (1 to 12).
    
    Can be called as:
        - `calendar_to_financial_month(2025, 4)` -> 1
        - `calendar_to_financial_month(4)` -> 1
        
    Args:
        year_or_month: If month is provided, this is the calendar year. Otherwise, this is calendar month.
        month: Optional calendar month (1 to 12).
        
    Returns:
        int: Financial month number (1 = October, ..., 3 = December, 4 = January, ..., 12 = September).
        
    Raises:
        ValueError: If calendar month is not between 1 and 12.
    """
    cal_month = month if month is not None else year_or_month

    if not isinstance(cal_month, int) or not (1 <= cal_month <= 12):
        raise ValueError(f"Invalid calendar month: {cal_month}. Month must be an integer between 1 and 12.")

    if 10 <= cal_month <= 12:
        return cal_month - 9
    else:
        return cal_month + 3


def _fy_month_to_calendar(start_year: int, fm: int) -> tuple[int, int, str]:
    """Helper to convert start_year and financial month number (1-12) to (cal_year, cal_month, month_name)."""
    if 1 <= fm <= 3:
        cal_month = fm + 9
        cal_year = start_year
    else:
        cal_month = fm - 3
        cal_year = start_year + 1
    return cal_year, cal_month, CALENDAR_MONTH_NAMES[cal_month]


def financial_year_to_calendar_month(
    financial_year: str | int, financial_month: int | str
) -> str:
    """Convert a financial year and financial month to calendar month and year string.
    
    Args:
        financial_year: Financial year string (e.g., "FY2025-26", "2025-26") or start year integer (2025).
        financial_month: Financial month number (1 to 12).
        
    Returns:
        str: Calendar month and year formatted string (e.g., "April 2025", "January 2026").
        
    Raises:
        ValueError: If financial_year or financial_month is invalid.
    """
    start_year, _, _ = parse_financial_year(financial_year)
    fm = parse_financial_month(financial_month)
    cal_year, cal_month, month_name = _fy_month_to_calendar(start_year, fm)
    return f"{month_name} {cal_year}"


def get_financial_quarter_months(quarter: int | str) -> list[int]:
    """Get the financial month numbers (1-12) for a given financial quarter (Q1 to Q4).
    
    Args:
        quarter: Quarter identifier (1, 2, 3, 4, "1", "Q1", "Q2", etc.).
        
    Returns:
        list[int]: List of 3 financial month numbers.
        
    Raises:
        ValueError: If quarter is invalid.
    """
    if isinstance(quarter, str):
        match = re.search(r"Q?(\d)", quarter, re.IGNORECASE)
        if match:
            q_num = int(match.group(1))
        else:
            raise ValueError(f"Invalid quarter format: '{quarter}'. Expected 'Q1', 'Q2', 'Q3', or 'Q4'.")
    else:
        q_num = quarter

    if q_num not in QUARTER_TO_FY_MONTHS:
        raise ValueError(f"Invalid quarter: {quarter}. Quarter must be 1, 2, 3, or 4 (or Q1-Q4).")

    return QUARTER_TO_FY_MONTHS[q_num]


# ====================================================================
# Tool Functions Exposed for Agent / Function Calling
# ====================================================================

def convert_financial_month(
    financial_year: str | int, financial_month: int | str
) -> dict[str, Any]:
    """Deterministic tool to convert an Indian Financial Year and Financial Month into calendar date information.
    
    Tool Name:
        convert_financial_month
        
    Purpose:
        Deterministically converts Indian financial year and financial month (1-12)
        to calendar year, calendar month, and 'YYYY-MM' database query format.
        
    Parameters:
        financial_year (str): The financial year (e.g., 'FY2025-26', 'FY25-26', '2025-26').
        financial_month (int | str): Financial month number (1 to 12, where 1=April, 10=January).
        
    Returns:
        dict: Structured mapping containing:
            - financial_year (str): Canonical FY string (e.g., 'FY2025-26')
            - financial_month (int): Financial month number (e.g., 10)
            - calendar_year (int): Calendar year (e.g., 2026)
            - calendar_month (int): Calendar month number (e.g., 1)
            - calendar_month_name (str): Month name (e.g., 'January')
            - calendar_date_month (str): Formatted 'YYYY-MM' (e.g., '2026-01')
    """
    logger.info("Executing convert_financial_month(financial_year=%r, financial_month=%r)", financial_year, financial_month)

    start_year, _, canonical_fy = parse_financial_year(financial_year)
    fm = parse_financial_month(financial_month)
    cal_year, cal_month, month_name = _fy_month_to_calendar(start_year, fm)
    calendar_date_month = f"{cal_year:04d}-{cal_month:02d}"

    return {
        "financial_year": canonical_fy,
        "financial_month": fm,
        "calendar_year": cal_year,
        "calendar_month": cal_month,
        "calendar_month_name": month_name,
        "calendar_date_month": calendar_date_month,
    }


def convert_calendar_to_financial(year: int, month: int | str) -> dict[str, Any]:
    """Deterministic tool to convert calendar year and month into Indian Financial Year and Month details.
    
    Tool Name:
        convert_calendar_to_financial
        
    Parameters:
        year (int): Calendar year (e.g., 2026).
        month (int | str): Calendar month (1-12 or month name e.g., 'January' or '12').
        
    Returns:
        dict: Structured mapping with financial_year, financial_month, quarter, and calendar details.
    """
    logger.info("Executing convert_calendar_to_financial(year=%r, month=%r)", year, month)

    if isinstance(month, str):
        cleaned_m = month.strip().lower()
        if cleaned_m.isdigit():
            m_int = int(cleaned_m)
        elif cleaned_m in MONTH_NAME_TO_INT:
            m_int = MONTH_NAME_TO_INT[cleaned_m]
        else:
            raise ValueError(f"Invalid calendar month name: '{month}'")
    else:
        m_int = month

    if not (1 <= m_int <= 12):
        raise ValueError(f"Invalid calendar month: {m_int}. Must be between 1 and 12.")

    fy_str = calendar_to_financial_year(year, m_int)
    fy_month = calendar_to_financial_month(year, m_int)

    # Determine quarter
    if 1 <= fy_month <= 3:
        quarter = "Q1"
    elif 4 <= fy_month <= 6:
        quarter = "Q2"
    elif 7 <= fy_month <= 9:
        quarter = "Q3"
    else:
        quarter = "Q4"

    return {
        "calendar_year": year,
        "calendar_month": m_int,
        "calendar_month_name": CALENDAR_MONTH_NAMES[m_int],
        "financial_year": fy_str,
        "financial_month": fy_month,
        "quarter": quarter,
    }


def convert_financial_quarter(
    financial_year: str | int, quarter: int | str
) -> dict[str, Any]:
    """Deterministic tool to convert an Indian Financial Year and Quarter into its constituent calendar months.
    
    Tool Name:
        convert_financial_quarter
        
    Parameters:
        financial_year (str): Financial year (e.g., 'FY2025-26').
        quarter (int | str): Financial quarter (1-4 or 'Q1'-'Q4').
        
    Returns:
        dict: Structured mapping with quarter, financial months, calendar 'YYYY-MM' list, and month names.
    """
    logger.info("Executing convert_financial_quarter(financial_year=%r, quarter=%r)", financial_year, quarter)
    start_year, _, canonical_fy = parse_financial_year(financial_year)
    fy_months = get_financial_quarter_months(quarter)

    # Normalize quarter name
    q_num = 1 if fy_months == [1, 2, 3] else (2 if fy_months == [4, 5, 6] else (3 if fy_months == [7, 8, 9] else 4))
    quarter_name = f"Q{q_num}"

    cal_dates = []
    cal_names = []

    for fm in fy_months:
        cal_yr, cal_m, month_name = _fy_month_to_calendar(start_year, fm)
        cal_dates.append(f"{cal_yr:04d}-{cal_m:02d}")
        cal_names.append(f"{month_name} {cal_yr}")

    return {
        "financial_year": canonical_fy,
        "quarter": quarter_name,
        "financial_months": fy_months,
        "calendar_months": cal_dates,
        "calendar_month_names": cal_names,
    }
