"""Interactive CLI entrypoint for Agentic AI Finance POC with FastMCP Server integration.

Usage:
    python -m app.main
"""

from __future__ import annotations

import asyncio
import sys
from app.agent import FinanceAgent


def display_banner() -> None:
    """Print the interactive CLI header banner."""
    print("=" * 55)
    print(" Agentic AI Finance Assistant")
    print(" Powered by Google Gemini & FastMCP Server")
    print("=" * 55)
    print()
    print("Type a finance or financial-year question.")
    print("Type 'exit' or 'quit' to end session.\n")


async def async_main() -> None:
    """Main CLI execution loop using asynchronous MCP Agent."""
    display_banner()
    agent = FinanceAgent()

    if not agent.is_configured():
        print("[Notice] Gemini API key is not configured. Add GEMINI_API_KEY to your .env file.")
        print("[Notice] You can still run pytest or test_client.py to test MCP tools independently.\n")

    while True:
        try:
            # Non-blocking input handling in executor or standard prompt
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!")
                break

            print("-" * 55)
            response = await agent.ask_async(user_input)
            print(f"Assistant:\n{response}")
            print("-" * 55)
            print()

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] An unexpected error occurred: {e}\n")


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
