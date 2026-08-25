"""Gemini AI Agent with Model Context Protocol (MCP) Client integration.

Connects to the FastMCP server (mcp_server/server.py) over stdio transport,
dynamically discovers all registered tools via MCP protocol, and executes
tool calls exclusively through the MCP server.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

SYSTEM_INSTRUCTION = """You are a finance data assistant for an Agentic AI proof-of-concept.

You answer questions using only financial data retrieved through the provided MCP tools.

Indian Financial Year (FY) Convention:
- An Indian Financial Year runs from April 1 to March 31.
- FY month numbering: Month 1 = April, Month 2 = May, Month 3 = June, Month 4 = July, Month 5 = August, Month 6 = September, Month 7 = October, Month 8 = November, Month 9 = December, Month 10 = January (of next calendar year), Month 11 = February, Month 12 = March.
- Quarters: Q1 (Apr-Jun / Months 1-3), Q2 (Jul-Sep / Months 4-6), Q3 (Oct-Dec / Months 7-9), Q4 (Jan-Mar / Months 10-12).

Workflow for Financial-Year / Month Questions:
- When a user question contains financial-year or financial-month terminology (e.g., 'FY2025-26', 'FY25-26', 'financial month 10', 'FY month 4', 'fiscal year', 'Q1 FY2025-26'):
  1. Call the deterministic conversion tool (`convert_financial_month`, `convert_financial_quarter`, or `convert_calendar_to_financial`) first to obtain the exact calendar date (`YYYY-MM`).
  2. Do not attempt to compute or guess dates manually; always use the deterministic conversion tools.
  3. Then call the PostgreSQL database tool (`get_financial_data`, `compare_forecast`, etc.) with the resulting calendar month (`YYYY-MM`).
- For questions asking purely about financial year concepts, conversions, or quarters (e.g., 'What is Q1 FY2025-26?', 'Which calendar month is FY month 10?'), invoke the conversion tool and provide a clear explanation to the user.

Workflow for Standard Calendar Questions:
- For normal calendar-month questions (e.g., 'Show me actual for ORG003 in January 2026', '2026-03'), do NOT use the financial-year conversion tools unnecessarily. Call the database tools directly.

General Rules:
- Whenever a question requires financial data, use the appropriate MCP tool.
- Never invent financial values or make up database records.
- Never generate or execute arbitrary SQL.
- If requested information is not available in the database, clearly inform the user that it is unavailable.
- When presenting calculations, use the values returned by the tools.
- Be concise and clear."""


def _clean_schema_for_gemini(schema: Any) -> Any:
    """Recursively clean JSON Schema for Google Gemini API OpenAPI compatibility.
    
    Removes unsupported keys like '$schema', 'title', 'additionalProperties',
    'additional_properties' that Gemini rejects.
    """
    if not isinstance(schema, dict):
        return schema
    cleaned: dict[str, Any] = {}
    for k, v in schema.items():
        if k in ("$schema", "title", "additionalProperties", "additional_properties"):
            continue
        if isinstance(v, dict):
            cleaned[k] = _clean_schema_for_gemini(v)
        elif isinstance(v, list):
            cleaned[k] = [
                _clean_schema_for_gemini(x) if isinstance(x, dict) else x for x in v
            ]
        else:
            cleaned[k] = v
    return cleaned


def _format_error(e: BaseException) -> str:
    """Recursively extract error message from Exception and ExceptionGroup."""
    err_msgs: list[str] = []
    if hasattr(e, "exceptions"):
        for sub_e in getattr(e, "exceptions", []):
            err_msgs.append(_format_error(sub_e))
        combined = " | ".join(err_msgs)
    else:
        combined = str(e)

    if "429" in combined or "RESOURCE_EXHAUSTED" in combined or "quota" in combined.lower():
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", combined, re.IGNORECASE)
        if match:
            wait_sec = int(float(match.group(1))) + 1
            return (
                f"Gemini API rate limit reached (Free Tier quota). "
                f"Please wait {wait_sec} seconds before sending your next request."
            )
        return "Gemini API rate limit reached (Free Tier quota). Please wait a few seconds before trying again."
    if "503" in combined or "UNAVAILABLE" in combined:
        return "Gemini service temporarily unavailable. Please try again in a few moments."
    return combined


class FinanceAgent:
    """Agentic AI coordinator interfacing between Google Gemini and the FastMCP Server."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        server_script: str | Path | None = None,
    ):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

        if not self.api_key or self.api_key in ("CHANGE_ME", "your_gemini_api_key_here"):
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        if server_script is None:
            self.server_script = (
                Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"
            )
        else:
            self.server_script = Path(server_script).resolve()

        self.discovered_tools: list[str] = []

    def is_configured(self) -> bool:
        """Check whether the Gemini API key is configured."""
        return self.client is not None

    async def ask_async(self, query: str) -> str:
        """Process a user query asynchronously using MCP tool calling.
        
        Args:
            query: Natural language financial question from user.
            
        Returns:
            Final natural language response string from Gemini.
        """
        if not self.is_configured():
            return "Gemini API key is not configured. Add GEMINI_API_KEY to your .env file."

        # Setup MCP stdio server parameters
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script)],
            env=None,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 1. MCP Handshake
                    await session.initialize()

                    # 2. Dynamic Tool Discovery from FastMCP Server
                    tools_resp = await session.list_tools()
                    self.discovered_tools = [t.name for t in tools_resp.tools]

                    func_decls = [
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description or "",
                            parameters=_clean_schema_for_gemini(tool.inputSchema),
                        )
                        for tool in tools_resp.tools
                    ]

                    gemini_tool_config = types.Tool(function_declarations=func_decls)
                    config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=[gemini_tool_config],
                        temperature=0.0,
                    )

                    # 3. Execute chat session with MCP tool loop
                    return await self._execute_mcp_chat(session, query, self.model, config)

        except BaseException as e:
            return _format_error(e)

    def ask(self, query: str) -> str:
        """Synchronous wrapper for ask_async for CLI and test compatibility."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, self.ask_async(query)).result()
        else:
            return asyncio.run(self.ask_async(query))

    async def _execute_mcp_chat(
        self,
        session: ClientSession,
        query: str,
        model_name: str,
        config: types.GenerateContentConfig,
    ) -> str:
        """Execute multi-turn tool interaction loop over MCP stdio session."""
        chat = self.client.chats.create(model=model_name, config=config)

        # Initial prompt to Gemini with backoff
        for attempt in range(4):
            try:
                response = chat.send_message(query)
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                    wait_sec = int(float(match.group(1))) + 1 if match else 5
                    if attempt < 3:
                        print(f"[Gemini Rate Limit] Waiting {wait_sec}s for free tier quota reset...")
                        await asyncio.sleep(wait_sec)
                        continue
                if "503" in err_str and attempt < 3:
                    await asyncio.sleep(2)
                    continue
                raise

        max_turns = 6
        turns = 0

        while response.function_calls and turns < max_turns:
            turns += 1
            for call in response.function_calls:
                fn_name = call.name
                fn_args = dict(call.args) if call.args else {}

                print(f"\n[MCP Client -> Server] Calling tool: '{fn_name}' with args: {fn_args}")

                # Call tool via Model Context Protocol
                try:
                    mcp_res = await session.call_tool(fn_name, fn_args)
                    res_text = mcp_res.content[0].text if mcp_res.content else "{}"

                    # Parse JSON or wrap raw text
                    if res_text.strip().startswith("{") or res_text.strip().startswith("["):
                        try:
                            parsed_res = json.loads(res_text)
                        except Exception:
                            parsed_res = res_text
                    else:
                        parsed_res = res_text

                except Exception as tool_err:
                    print(f"[MCP Tool Error]: {tool_err}")
                    parsed_res = {"error": str(tool_err)}

                # Send tool response back to Gemini with backoff
                for attempt in range(4):
                    try:
                        response = chat.send_message(
                            types.Part.from_function_response(
                                name=fn_name,
                                response={"result": parsed_res},
                            )
                        )
                        break
                    except Exception as e:
                        err_str = str(e)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                            wait_sec = int(float(match.group(1))) + 1 if match else 5
                            if attempt < 3:
                                print(f"[Gemini Rate Limit] Waiting {wait_sec}s for free tier quota reset...")
                                await asyncio.sleep(wait_sec)
                                continue
                        if "503" in err_str and attempt < 3:
                            await asyncio.sleep(2)
                            continue
                        raise

        final_text = response.text or "No response generated."
        print(f"\n[Gemini Response]\n{final_text}\n")
        return final_text
