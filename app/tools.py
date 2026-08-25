"""Finance Toolset for Agentic AI.

Provides safe, parameterized query tools to access and analyze financial forecasts
and actuals data stored in PostgreSQL.
"""

from __future__ import annotations

import re
from typing import Any

from app.database import execute_query, execute_single_query
from app.skills.financial_year import (
    convert_calendar_to_financial,
    convert_financial_month,
    convert_financial_quarter,
)



def _validate_org_id(org_id: str) -> str:
    """Validate and sanitize organization identifier.
    
    Args:
        org_id: Organization ID string (e.g., 'ORG001').
        
    Returns:
        Cleaned org_id string.
        
    Raises:
        ValueError: If org_id is empty or contains invalid characters.
    """
    if not isinstance(org_id, str) or not org_id.strip():
        raise ValueError("Organization ID must be a non-empty string (e.g., 'ORG001').")
    clean_org = org_id.strip().upper()
    if not re.match(r"^[A-Z0-9_-]{2,20}$", clean_org):
        raise ValueError(f"Invalid organization ID format: '{org_id}'. Expected format like 'ORG001'.")
    return clean_org


def _validate_month(month: str | None) -> str | None:
    """Validate and normalize month format.
    
    Accepts 'YYYY-MM' (e.g. '2026-03') or 'YYYY-MM-DD' (e.g. '2026-03-01').
    
    Args:
        month: Month string or None.
        
    Returns:
        Normalized month string in 'YYYY-MM' format, or None.
        
    Raises:
        ValueError: If month string does not match expected format.
    """
    if month is None:
        return None
    if not isinstance(month, str) or not month.strip():
        return None
    clean_month = month.strip()
    match = re.match(r"^(\d{4})-(\d{2})(?:-\d{2})?$", clean_month)
    if not match:
        raise ValueError(f"Invalid month format: '{month}'. Expected format 'YYYY-MM' (e.g., '2026-03').")
    year, m = match.groups()
    m_int = int(m)
    if not (1 <= m_int <= 12):
        raise ValueError(f"Invalid month value in '{month}'. Month must be between 01 and 12.")
    return f"{year}-{m}"


def _validate_limit(limit: int) -> int:
    """Validate limit parameter.
    
    Args:
        limit: Number of records to return.
        
    Returns:
        Validated integer limit.
        
    Raises:
        ValueError: If limit is not an integer or is out of allowed range (1 to 50).
    """
    try:
        limit_int = int(limit)
    except (ValueError, TypeError):
        raise ValueError(f"Limit must be an integer, got: {limit}")
    if limit_int < 1 or limit_int > 50:
        raise ValueError(f"Limit must be between 1 and 50, got: {limit_int}")
    return limit_int


def get_financial_data(org_id: str, month: str | None = None) -> list[dict[str, Any]]:
    """Retrieve financial forecast and actual data for an organization.
    
    Tool Name:
        get_financial_data
        
    Purpose:
        Retrieve financial forecast and actual data for a specific organization
        and optionally a specific month.
        
    Parameters:
        org_id (str): The organization identifier (e.g., 'ORG001', 'ORG002').
        month (str | None): Optional month filter in 'YYYY-MM' format (e.g., '2026-03').
        
    Returns:
        list[dict]: List of matching records containing 'id', 'org_id', 'month',
                    'forecast', and 'actual'.
                    
    Example Use Case:
        Use when the user asks for financial records for a specific organization
        or month (e.g., "What was the actual value for ORG001 in March 2026?").
    """
    print(f"[Tool] Executing get_financial_data(org_id='{org_id}', month={month!r})")
    clean_org = _validate_org_id(org_id)
    clean_month = _validate_month(month)

    if clean_month is not None:
        query = """
            SELECT id, org_id, month, forecast, actual
            FROM financial_forecasts
            WHERE org_id = %s AND TO_CHAR(month, 'YYYY-MM') = %s
            ORDER BY month ASC;
        """
        params = (clean_org, clean_month)
    else:
        query = """
            SELECT id, org_id, month, forecast, actual
            FROM financial_forecasts
            WHERE org_id = %s
            ORDER BY month ASC;
        """
        params = (clean_org,)

    return execute_query(query, params)


def get_org_summary(org_id: str) -> dict[str, Any]:
    """Calculate overall forecast, actual, variance, and variance percentage for an organization.
    
    Tool Name:
        get_org_summary
        
    Purpose:
        Calculate total forecast, total actual, net variance (actual - forecast),
        and variance percentage for an organization across all months.
        
    Parameters:
        org_id (str): The organization identifier (e.g., 'ORG001', 'ORG003').
        
    Returns:
        dict: Summary containing 'org_id', 'total_forecast', 'total_actual',
              'variance', and 'variance_percentage'.
              
    Formula:
        variance = total_actual - total_forecast
        variance_percentage = ((total_actual - total_forecast) / total_forecast) * 100
        
    Example Use Case:
        Use when the user asks for overall forecast, actual, variance, or financial
        performance for an organization (e.g., "Give me the total forecast and actual for ORG003.").
    """
    print(f"[Tool] Executing get_org_summary(org_id='{org_id}')")
    clean_org = _validate_org_id(org_id)

    query = """
        SELECT 
            COALESCE(SUM(forecast), 0) AS total_forecast,
            COALESCE(SUM(actual), 0) AS total_actual,
            COUNT(*) AS record_count
        FROM financial_forecasts
        WHERE org_id = %s;
    """
    row = execute_single_query(query, (clean_org,))
    if not row or row.get("record_count", 0) == 0:
        return {
            "org_id": clean_org,
            "total_forecast": 0.0,
            "total_actual": 0.0,
            "variance": 0.0,
            "variance_percentage": 0.0,
            "note": f"No financial records found for organization {clean_org}."
        }

    total_forecast = float(row["total_forecast"])
    total_actual = float(row["total_actual"])
    variance = total_actual - total_forecast
    
    # Safe division
    if total_forecast != 0:
        variance_percentage = round((variance / total_forecast) * 100.0, 2)
    else:
        variance_percentage = 0.0

    return {
        "org_id": clean_org,
        "total_forecast": total_forecast,
        "total_actual": total_actual,
        "variance": round(variance, 2),
        "variance_percentage": variance_percentage,
    }


def compare_forecast(org_id: str, month: str | None = None) -> list[dict[str, Any]]:
    """Compare forecast against actual performance for an organization and classify performance.
    
    Tool Name:
        compare_forecast
        
    Purpose:
        Compare forecast vs actual values and evaluate whether performance was
        'above_forecast', 'below_forecast', or 'on_forecast'.
        
    Parameters:
        org_id (str): The organization identifier (e.g., 'ORG001', 'ORG005').
        month (str | None): Optional month filter in 'YYYY-MM' format (e.g., '2026-04').
        
    Returns:
        list[dict]: List of records containing 'org_id', 'month', 'forecast',
                    'actual', 'variance', 'variance_percentage', and 'performance'.
                    
    Performance Rules:
        - If actual > forecast: 'above_forecast'
        - If actual < forecast: 'below_forecast'
        - If actual == forecast: 'on_forecast'
        
    Example Use Case:
        Use when the user asks whether actual performance was above or below forecast
        (e.g., "Compare ORG005 forecast against actual for April 2026.").
    """
    print(f"[Tool] Executing compare_forecast(org_id='{org_id}', month={month!r})")
    records = get_financial_data(org_id, month)
    results = []

    for rec in records:
        forecast = float(rec["forecast"])
        actual = float(rec["actual"])
        variance = actual - forecast

        if forecast != 0:
            var_pct = round((variance / forecast) * 100.0, 2)
        else:
            var_pct = 0.0

        if actual > forecast:
            perf = "above_forecast"
        elif actual < forecast:
            perf = "below_forecast"
        else:
            perf = "on_forecast"

        results.append({
            "org_id": rec["org_id"],
            "month": rec["month"],
            "forecast": forecast,
            "actual": actual,
            "variance": round(variance, 2),
            "variance_percentage": var_pct,
            "performance": perf,
        })

    return results


def get_top_variances(limit: int = 5) -> list[dict[str, Any]]:
    """Find the records with the largest absolute variance between forecast and actual.
    
    Tool Name:
        get_top_variances
        
    Purpose:
        Retrieve top financial records ranked by the largest absolute difference
        between forecast and actual across all organizations and months.
        
    Parameters:
        limit (int): Number of top records to return (default 5, between 1 and 50).
        
    Returns:
        list[dict]: List of records with 'org_id', 'month', 'forecast', 'actual',
                    'variance', and 'variance_percentage', ordered by largest absolute variance.
                    
    Example Use Case:
        Use when the user asks which organization or month had the largest difference
        between forecast and actual (e.g., "Which month had the largest variance?").
    """
    print(f"[Tool] Executing get_top_variances(limit={limit})")
    clean_limit = _validate_limit(limit)

    query = """
        SELECT 
            org_id,
            month,
            forecast,
            actual,
            (actual - forecast) AS variance,
            CASE 
                WHEN forecast != 0 THEN ROUND(((actual - forecast) / forecast * 100.0)::numeric, 2)
                ELSE 0.0 
            END AS variance_percentage
        FROM financial_forecasts
        ORDER BY ABS(actual - forecast) DESC, month ASC
        LIMIT %s;
    """
    rows = execute_query(query, (clean_limit,))
    # Ensure numerical types are clean floats
    for row in rows:
        row["forecast"] = float(row["forecast"])
        row["actual"] = float(row["actual"])
        row["variance"] = float(row["variance"])
        row["variance_percentage"] = float(row["variance_percentage"])
    return rows


# Registry of permitted tools
AVAILABLE_TOOLS = {
    "get_financial_data": get_financial_data,
    "get_org_summary": get_org_summary,
    "compare_forecast": compare_forecast,
    "get_top_variances": get_top_variances,
    "convert_financial_month": convert_financial_month,
    "convert_calendar_to_financial": convert_calendar_to_financial,
    "convert_financial_quarter": convert_financial_quarter,
}

