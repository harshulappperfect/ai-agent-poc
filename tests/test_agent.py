"""Automated tests for Gemini AI Agent configuration and MCP tool integration."""

import pytest
from app.agent import FinanceAgent, SYSTEM_INSTRUCTION
from app.tools import AVAILABLE_TOOLS


def test_agent_unconfigured_without_api_key():
    """Verify that agent gracefully handles missing API key."""
    agent = FinanceAgent(api_key="")
    assert not agent.is_configured()
    response = agent.ask("What was the actual value for ORG001 in March 2026?")
    assert "Gemini API key is not configured" in response


def test_agent_system_instruction():
    """Verify system instructions contain key constraints."""
    assert "You are a finance data assistant" in SYSTEM_INSTRUCTION
    assert "Never generate or execute arbitrary SQL" in SYSTEM_INSTRUCTION
    assert "Never invent financial values" in SYSTEM_INSTRUCTION


def test_tool_declarations_match_available_tools():
    """Verify all defined tools map to permitted MCP functions."""
    declared_names = set(AVAILABLE_TOOLS.keys())
    
    expected_tools = {
        "get_financial_data",
        "get_org_summary",
        "compare_forecast",
        "get_top_variances",
        "convert_financial_month",
        "convert_calendar_to_financial",
        "convert_financial_quarter",
    }
    assert declared_names == expected_tools
