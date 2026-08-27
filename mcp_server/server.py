from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Ensure project root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools import (
    compare_forecast,
    convert_calendar_to_financial,
    convert_financial_month,
    convert_financial_quarter,
    get_financial_data,
    get_org_summary,
    get_top_variances,
)

mcp = FastMCP("Finance MCP Server")

# Register database analysis tools with FastMCP
mcp.tool()(get_financial_data)
mcp.tool()(get_org_summary)
mcp.tool()(compare_forecast)
mcp.tool()(get_top_variances)

# Register financial year skill tools with FastMCP
mcp.tool()(convert_financial_month)
mcp.tool()(convert_calendar_to_financial)
mcp.tool()(convert_financial_quarter)


if __name__ == "__main__":
    mcp.run()
