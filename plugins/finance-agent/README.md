# 📊 Finance Agent Plugin — Setup & User Guide

Welcome to the **Finance Agent Plugin**! This is a self-contained, plug-and-play **Model Context Protocol (MCP)** plugin that equips any AI model (Gemini, Claude, GPT-4) or AI IDE (Cursor, VS Code Antigravity, Claude Desktop) with 9-table PostgreSQL database query tools, defense-in-depth SQL security, and Indian Financial Year date conversion skills.

---

## 📌 Features

- **9-Table Relational Analytics**: Inspect table schemas and query budgets, actual forecasts, invoices, transactions, departments, employees, vendors, and projects.
- **Defense-in-Depth SQL Security**: Built-in AST and regex safety validator that strictly permits read-only `SELECT` and `WITH` (CTE) statements while blocking `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and multi-statement attacks.
- **Indian Financial Year Engine**: Converts Indian Financial Year notation (Oct 1 – Sep 30, FY months 1-12, Quarters Q1-Q4) to exact calendar dates (`YYYY-MM`).
- **Standardized MCP Interface**: Communicates over standard input/output (`stdio`), making it cross-compatible with Python, Node.js, Go, or any MCP client application.

---

## 🛠 Prerequisites

Before setting up the plugin, make sure you have:

1. **Python 3.10 or higher** installed (`python --version`).
2. **PostgreSQL** database running (or Docker PostgreSQL container) containing your financial schema.
3. A PostgreSQL user with read permissions (e.g. `agent_readonly`).

---

## 🚀 Step-by-Step Installation & Setup

### Step 1: Add the Plugin to Your Project

Clone or download this plugin repository into your project directory:

```powershell
# As a Git Submodule (Recommended for Git projects)
git submodule add https://github.com/harshulappperfect/finance-agent-plugin.git plugins/finance-agent

# OR Clone directly
git clone https://github.com/harshulappperfect/finance-agent-plugin.git plugins/finance-agent
```

---

### Step 2: Install Python Dependencies

Navigate to your project directory and install the required dependencies:

```powershell
pip install -r plugins/finance-agent/requirements.txt
```

---

### Step 3: Configure Database Environment Variables

Set your PostgreSQL connection details using environment variables or a `.env` file in your root project directory:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mydatabase
DATABASE_USER=agent_readonly
DATABASE_PASSWORD=your_database_password
```

---

## 🔌 How to Connect the Plugin to Your AI Tool

### Option A: Using AI IDEs or Apps (Claude Desktop, Cursor, Antigravity, VS Code)

Open your application's `mcp_config.json` file and add the server configuration:

```json
{
  "mcpServers": {
    "finance-agent": {
      "command": "python",
      "args": [
        "C:/path/to/your-project/plugins/finance-agent/server/server.py"
      ],
      "env": {
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "mydatabase",
        "DATABASE_USER": "agent_readonly",
        "DATABASE_PASSWORD": "your_database_password"
      }
    }
  }
}
```
*(Replace `C:/path/to/your-project/` with the absolute path to your project folder).*

---

### Option B: Using in a Custom Python AI Agent

If you are building your own Python AI agent, launch the plugin server script as an `stdio` subprocess:

```python
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Resolve path to the plugin server executable
SERVER_SCRIPT = Path("plugins/finance-agent/server/server.py").resolve()

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(SERVER_SCRIPT)],
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List all 9 registered MCP tools
            tools_res = await session.list_tools()
            print("Connected Tools:", [t.name for t in tools_res.tools])

            # Example: Execute tool call
            res = await session.call_tool("get_database_schema", {})
            print("Database Schema:", res.content[0].text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 🧰 Included MCP Tools (9 Tools)

| Tool Name | Description | Example Usage |
| :--- | :--- | :--- |
| `get_database_schema` | Returns column names, data types, and primary/foreign keys across all 9 tables. | `get_database_schema()` |
| `run_read_only_query` | Executes safe, read-only `SELECT` or `WITH` CTE queries (max 100 rows). | `run_read_only_query(query="SELECT * FROM budgets")` |
| `get_financial_data` | Retrieves monthly forecast vs actual records for an organization ID. | `get_financial_data(org_id="ORG001", month="2026-03")` |
| `get_org_summary` | Calculates total forecast, total actual, and net variance for an organization. | `get_org_summary(org_id="ORG003")` |
| `compare_forecast` | Evaluates performance (`above_forecast`, `below_forecast`, `on_forecast`). | `compare_forecast(org_id="ORG005", month="2026-04")` |
| `get_top_variances` | Ranks top financial records by largest absolute variance. | `get_top_variances(limit=5)` |
| `convert_financial_month` | Converts Indian FY month numbers (Month 1 = Oct, Month 4 = Jan) to calendar dates. | `convert_financial_month(financial_year="FY2025-26", financial_month=4)` |
| `convert_calendar_to_financial` | Maps calendar dates (`2026-02`) to Indian FY year, month, and quarter. | `convert_calendar_to_financial(year=2026, month=2)` |
| `convert_financial_quarter` | Converts FY quarters (`Q1`-`Q4`) to calendar month ranges (`YYYY-MM`). | `convert_financial_quarter(financial_year="FY2025-26", quarter=1)` |

---

## 🧠 Included Agent Skills

The plugin includes runbooks in `skills/` to guide your AI model's reasoning:

- **`financial-analysis/SKILL.md`**: Runbook for 9-table multi-table analysis (Budget vs Actual variance, Vendor spend breakdown, Department payroll aggregations).
- **`financial-reporting/SKILL.md`**: Standards for formatting executive summary reports and markdown tables.
- **`financial-year/SKILL.md`**: Reference rules for Indian Financial Year conventions (Oct 1 – Sep 30).

---

## ❓ FAQs & Troubleshooting

- **Q: Why am I getting `Security Error: Only SELECT and WITH (CTE) queries are permitted`?**
  - *Answer*: The plugin strictly enforces read-only access. Write operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`) are blocked for database security.
- **Q: Why are results capped at 100 rows?**
  - *Answer*: To prevent un-capped `SELECT *` queries from overflowing your LLM's context window or system memory.

---

## 📜 License & Support

Distributed under the MIT License. Feel free to use, modify, and integrate into your AI projects!
