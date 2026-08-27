"""Automated test suite for MCP Server and Gemini MCP Agent Integration."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.agent import FinanceAgent

SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"


@pytest.mark.asyncio
async def test_mcp_server_tool_discovery():
    """Verify FastMCP server exposes all 7 required tools via MCP protocol."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init_res = await session.initialize()
            assert init_res.serverInfo.name == "Finance MCP Server"

            tools_resp = await session.list_tools()
            tool_names = {t.name for t in tools_resp.tools}

            expected_tools = {
                "get_financial_data",
                "get_org_summary",
                "compare_forecast",
                "get_top_variances",
                "convert_financial_month",
                "convert_calendar_to_financial",
                "convert_financial_quarter",
            }
            assert expected_tools.issubset(tool_names)


@pytest.mark.asyncio
async def test_mcp_tool_convert_financial_month():
    """Verify convert_financial_month executes over MCP stdio protocol."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "convert_financial_month",
                {"financial_year": "2025-2026", "financial_month": 8},
            )
            assert result.content
            data = json.loads(result.content[0].text)
            assert data["calendar_year"] == 2026
            assert data["calendar_month"] == 5
            assert data["calendar_month_name"] == "May"
            assert data["calendar_date_month"] == "2026-05"


@pytest.mark.asyncio
async def test_mcp_tool_convert_financial_quarter():
    """Verify convert_financial_quarter executes over MCP stdio protocol."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "convert_financial_quarter",
                {"financial_year": "FY2025-26", "quarter": 1},
            )
            assert result.content
            data = json.loads(result.content[0].text)
            assert data["quarter"] == "Q1"
            assert data["financial_months"] == [1, 2, 3]
            assert data["calendar_months"] == ["2025-10", "2025-11", "2025-12"]


@pytest.mark.asyncio
async def test_mcp_tool_convert_calendar_to_financial():
    """Verify convert_calendar_to_financial executes over MCP stdio protocol."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "convert_calendar_to_financial",
                {"year": 2026, "month": 2},
            )
            assert result.content
            data = json.loads(result.content[0].text)
            assert data["financial_year"] == "FY2025-26"
            assert data["financial_month"] == 5
            assert data["quarter"] == "Q2"


def test_agent_configuration():
    """Verify FinanceAgent initialization and API key check."""
    agent = FinanceAgent()
    assert agent.is_configured() is True
    assert agent.server_script.exists()


@pytest.mark.asyncio
async def test_agent_mcp_end_to_end_query():
    """Verify Gemini AI agent answers financial questions via FastMCP tool routing."""
    agent = FinanceAgent()
    if not agent.is_configured():
        pytest.skip("Gemini API key not configured.")

    response = await agent.ask_async("What is financial month 8 of FY2025-26?")
    assert "May" in response or "2026-05" in response
