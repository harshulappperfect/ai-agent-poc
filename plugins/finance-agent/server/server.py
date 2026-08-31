from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure plugin server directory is in sys.path when executed directly as a script
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

from tools import (
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

mcp = FastMCP("Finance Agent Plugin Server")

# Register financial query tools
mcp.tool()(get_financial_data)
mcp.tool()(get_org_summary)
mcp.tool()(compare_forecast)
mcp.tool()(get_top_variances)

# Register 9-table schema & dynamic read-only query tools
mcp.tool()(get_database_schema)
mcp.tool()(run_read_only_query)

# Register financial year conversion tools
mcp.tool()(convert_financial_month)
mcp.tool()(convert_calendar_to_financial)
mcp.tool()(convert_financial_quarter)

if __name__ == "__main__":
    mcp.run()
