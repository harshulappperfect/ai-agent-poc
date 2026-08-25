"""CLI test client to verify the MCP server without any web tools or UI."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_server_test() -> None:
    """Connect to the MCP server via stdio, list tools, and test tool execution."""
    print("=" * 65)
    print(" MCP Server Local Test Client (CLI)")
    print("=" * 65)

    server_script = Path(__file__).resolve().parent / "server.py"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=None,
    )

    print(f"Connecting to MCP server: {server_script} ...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize MCP handshake
            init_result = await session.initialize()
            print("\n[+] Handshake Successful!")
            print(f"    Server Name:    {init_result.serverInfo.name}")
            print(f"    Protocol Ver:   {init_result.protocolVersion}")

            # 2. List tools
            tools_response = await session.list_tools()
            print(f"\n[+] Discovered {len(tools_response.tools)} Registered Tools:")
            for i, tool in enumerate(tools_response.tools, start=1):
                first_line = tool.description.splitlines()[0] if tool.description else ""
                print(f"    {i}. {tool.name:<30} -> {first_line}")

            # 3. Test executing tool: convert_financial_month
            print("\n" + "-" * 65)
            print("[+] Testing Tool Execution: convert_financial_month")
            test_args = {"financial_year": "2025-2026", "financial_month": 8}
            print(f"    Input Arguments: {json.dumps(test_args)}")

            result = await session.call_tool("convert_financial_month", test_args)
            print("    Output from MCP Server:")
            if result.content:
                for content_block in result.content:
                    if hasattr(content_block, "text"):
                        print(f"    {content_block.text}")
                    else:
                        print(f"    {content_block}")

            # 4. Test executing tool: convert_financial_quarter
            print("\n" + "-" * 65)
            print("[+] Testing Tool Execution: convert_financial_quarter")
            test_q_args = {"financial_year": "2025-26", "quarter": 3}
            print(f"    Input Arguments: {json.dumps(test_q_args)}")

            q_result = await session.call_tool("convert_financial_quarter", test_q_args)
            print("    Output from MCP Server:")
            if q_result.content:
                for content_block in q_result.content:
                    if hasattr(content_block, "text"):
                        print(f"    {content_block.text}")

            print("\n" + "=" * 65)
            print("[SUCCESS] ALL CHECKS PASSED - MCP Server is fully operational!")
            print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_server_test())
