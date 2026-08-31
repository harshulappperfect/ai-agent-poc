"""Gemini AI Agent with Model Context Protocol (MCP) Client integration.

Connects to the FastMCP server (mcp_server/server.py) over stdio transport,
dynamically discovers all registered tools via MCP protocol, and executes
tool calls exclusively through the MCP server.
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

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

from app.memory import MemoryManager

# Load environment variables (override stale shell env vars)
load_dotenv(override=True)

MEMORY_COMPRESSION_THRESHOLD = 30

SYSTEM_INSTRUCTION = """You are an enterprise Financial Analyst AI with access to a PostgreSQL relational database containing 9 tables:

Database Schema Overview:
1. organizations (id, name, code, country)
2. departments (id, org_id, name, code)
3. employees (id, dept_id, name, email, role, salary, hire_date)
4. vendors (id, name, category, tax_id)
5. budgets (id, dept_id, fiscal_year, allocated_amount)
6. financial_forecasts (id, org_id, month, forecast, actual)
7. invoices (id, vendor_id, dept_id, invoice_date, amount, status)
8. transactions (id, invoice_date, dept_id, amount, transaction_type)
9. projects (id, dept_id, name, budget, status)

Financial Year (FY) Convention:
- An Indian Financial Year runs from October 1 to September 30.
- FY month numbering: Month 1 = October, Month 2 = November, Month 3 = December, Month 4 = January (next calendar year), Month 5 = February, Month 6 = March, Month 7 = April, Month 8 = May, Month 9 = June, Month 10 = July, Month 11 = August, Month 12 = September.
- Quarters: Q1 (Oct-Dec / Months 1-3), Q2 (Jan-Mar / Months 4-6), Q3 (Apr-Jun / Months 7-9), Q4 (Jul-Sep / Months 10-12).

Tool Usage Rules:
1. SCHEMA DISCOVERY: If you need to inspect exact column names or data types across tables, call `get_database_schema`.
2. DATE CONVERSION: For questions referencing Indian Financial Year notation (e.g. 'FY2025-26', 'Q1 FY26', 'financial month 10'), invoke conversion tools (`convert_financial_month`, `convert_financial_quarter`, `convert_calendar_to_financial`) first to obtain calendar dates ('YYYY-MM').
3. DYNAMIC SQL QUERIES: Use `run_read_only_query` to run safe SELECT or WITH statements when queries require JOINs, GROUP BY, aggregations (SUM, AVG, COUNT, MIN, MAX), subqueries, or multi-table analysis across any of the 9 tables.
4. SPECIFIC LOOKUPS: You can also use specialized tools like `get_financial_data` or `get_org_summary` for single-org forecast lookups.
5. SAFETY: Never attempt write or modification queries (INSERT, UPDATE, DELETE, DROP, ALTER). All queries are strictly read-only.
6. REPORTING: Present numeric values rounded to 2 decimal places and provide clear explanations alongside data tables."""


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
        memory_filepath: str | Path | None = None,
    ):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

        if not self.api_key or self.api_key in ("CHANGE_ME", "your_gemini_api_key_here"):
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        if server_script is None:
            self.server_script = (
                Path(__file__).resolve().parent.parent / "plugins" / "finance-agent" / "server" / "server.py"
            )
        else:
            self.server_script = Path(server_script).resolve()

        self.discovered_tools: list[str] = []
        self.chat_session: Any = None
        self.memory_manager = MemoryManager(filepath=memory_filepath)

    def is_configured(self) -> bool:
        """Check whether the Gemini API key is configured."""
        return self.client is not None

    def clear_memory(self) -> None:
        """Clear the conversational memory and start a fresh session."""
        self.chat_session = None
        self.memory_manager.clear_memory()
        logger.info("Conversational memory cleared.")

    def build_context(self, current_query: str) -> str:
        """Construct prompt context combining stored compressed summary,
        recent conversation history, and current user question.
        """
        summary = self.memory_manager.get_summary().strip()
        all_messages = self.memory_manager.get_all_messages()

        # Build list of prior messages excluding current question if already in memory
        recent_msgs = []
        for msg in all_messages:
            if (
                msg.get("role") == "user"
                and msg.get("content") == current_query
                and msg == all_messages[-1]
            ):
                continue
            recent_msgs.append(msg)

        context_parts = []
        if summary:
            context_parts.append(f"COMPRESSED HISTORICAL MEMORY:\n{summary}")

        if recent_msgs:
            history_lines = []
            for m in recent_msgs:
                role_label = "User" if m.get("role") == "user" else "Assistant"
                history_lines.append(f"{role_label}: {m.get('content', '')}")
            context_parts.append("RECENT CONVERSATION:\n" + "\n".join(history_lines))

        context_parts.append(f"CURRENT USER QUESTION:\n{current_query}")
        return "\n\n".join(context_parts)

    async def compress_memory(self) -> str:
        """Manually or automatically compact historical memory using Gemini.
        
        Summarizes active conversation history into a compact summary,
        archives older raw messages into JSON, and increments compression count.
        """
        if not self.is_configured():
            return "Gemini API key is not configured. Cannot compress memory."

        summary = self.memory_manager.get_summary()
        all_messages = self.memory_manager.get_all_messages()

        if not all_messages and not summary:
            return "[Memory] No active conversation messages to compress."

        prompt_parts = []
        if summary:
            prompt_parts.append(f"EXISTING SUMMARY:\n{summary}")

        if all_messages:
            history_lines = []
            for m in all_messages:
                role = "User" if m.get("role") == "user" else "Assistant"
                history_lines.append(f"{role}: {m.get('content', '')}")
            prompt_parts.append("CONVERSATION HISTORY TO COMPRESS:\n" + "\n".join(history_lines))

        prompt = "\n\n".join(prompt_parts)

        summarization_instruction = (
            "You are a financial memory compaction assistant.\n"
            "Your task is to summarize the preceding financial conversation into a concise, information-dense summary.\n\n"
            "PRESERVE ACCURATELY:\n"
            "- Organization IDs (e.g., ORG001, ORG003)\n"
            "- Financial years (e.g., FY2025-26), months, quarters\n"
            "- Financial values, actuals, forecasts, budget numbers, and variances\n"
            "- Specific user goals, requests, or questions asked\n"
            "- Important database findings or MCP tool results\n"
            "- Unresolved questions or key constraints needed for follow-up questions\n\n"
            "DISCARD:\n"
            "- Greetings, pleasantries, repetitive chatter\n"
            "- Duplicated explanation text\n"
            "- Unnecessary conversational filler\n\n"
            "Return ONLY the updated compressed summary text."
        )

        try:
            config = types.GenerateContentConfig(
                system_instruction=summarization_instruction,
                temperature=0.2,
            )
            res = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            new_summary = (res.text or "").strip()
            if not new_summary:
                return "[Error] Gemini returned an empty summary. Existing memory preserved."

            # Update summary and archive summarized active messages
            self.memory_manager.update_summary_and_archive(new_summary, keep_recent_count=4)
            self.chat_session = None  # Reset chat session state
            return (
                f"[Memory] Conversation compressed successfully. "
                f"Compression count: {self.memory_manager.get_compression_count()}."
            )
        except Exception as e:
            err_msg = _format_error(e)
            logger.error("Failed to compress memory: %s", err_msg)
            return f"[Error] Memory compression failed: {err_msg}. Existing memory preserved."

    async def ask_async(self, query: str) -> str:
        """Process a user query asynchronously using MCP tool calling.
        
        Args:
            query: Natural language financial question from user.
            
        Returns:
            Final natural language response string from Gemini.
        """
        if not self.is_configured():
            return "Gemini API key is not configured. Add GEMINI_API_KEY to your .env file."

        # Save user query to persistent memory
        self.memory_manager.add_user_message(query)

        # Check threshold for automatic memory compression
        if len(self.memory_manager.get_all_messages()) >= MEMORY_COMPRESSION_THRESHOLD:
            logger.info("Memory threshold reached (%d messages). Auto-compressing memory...", MEMORY_COMPRESSION_THRESHOLD)
            await self.compress_memory()

        # Build augmented prompt context from summary, history, and query
        context_prompt = self.build_context(query)

        # Reset chat session for fresh turn with persistent context
        self.chat_session = None

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
                    final_response = await self._execute_mcp_chat(session, context_prompt, self.model, config)

                    # Save assistant response to persistent memory
                    self.memory_manager.add_assistant_message(final_response)
                    return final_response

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

    async def _send_with_retry(self, chat: Any, message: Any) -> Any:
        """Send a message to Gemini chat with rate-limit retry and backoff logic."""
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                return await chat.send_message(message)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                    wait_sec = int(float(match.group(1))) + 1 if match else 3
                    # Fail fast if Google requests a long wait time (>5s) or if retry attempt reached
                    if wait_sec > 5 or attempt >= (max_attempts - 1):
                        raise
                    logger.info("[Gemini Rate Limit] Waiting %d s for quota reset...", wait_sec)
                    await asyncio.sleep(wait_sec)
                    continue
                if "503" in err_str and attempt < (max_attempts - 1):
                    logger.info("[Gemini Service Unavailable] Retrying...")
                    await asyncio.sleep(2)
                    continue
                raise

    async def _execute_mcp_chat(
        self,
        session: ClientSession,
        query: str,
        model_name: str,
        config: types.GenerateContentConfig,
    ) -> str:
        """Execute multi-turn interaction with persistent conversational memory over MCP stdio session."""
        if self.chat_session is None:
            self.chat_session = self.client.aio.chats.create(model=model_name, config=config)

        # Initial prompt to Gemini with backoff
        response = await self._send_with_retry(self.chat_session, query)

        max_turns = 6
        turns = 0

        while response.function_calls and turns < max_turns:
            turns += 1
            for call in response.function_calls:
                fn_name = call.name
                fn_args = dict(call.args) if call.args else {}

                logger.info("[MCP Client -> Server] Calling tool: '%s' with args: %s", fn_name, fn_args)

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
                    logger.info("MCP Tool Error: %r", tool_err)
                    parsed_res = {"error": str(tool_err)}

                # Send tool response back to Gemini with backoff
                func_part = types.Part.from_function_response(
                    name=fn_name,
                    response={"result": parsed_res},
                )
                response = await self._send_with_retry(self.chat_session, func_part)

        final_text = (response.text or "").strip()
        if not final_text and hasattr(response, "candidates") and response.candidates:
            try:
                parts = response.candidates[0].content.parts or []
                text_parts = [p.text for p in parts if getattr(p, "text", None)]
                if text_parts:
                    final_text = "\n".join(text_parts).strip()
            except Exception:
                pass

        final_text = final_text or "No response generated."
        logger.info("Gemini Response:\n%s", final_text)
        return final_text

