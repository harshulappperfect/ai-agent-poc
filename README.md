# Agentic AI Finance POC — Gemini + FastMCP + PostgreSQL

A modular, production-ready Proof of Concept (POC) demonstrating natural-language financial data analysis powered by **Google Gemini** (`gemini-3.5-flash-lite`), the **Model Context Protocol (FastMCP)** Python SDK, and a local **PostgreSQL** database running in Docker.

The Gemini AI model communicates with financial data and calendar conversion skills exclusively through the **Model Context Protocol (MCP)**—dynamically discovering tools and executing them over `stdio` without hardcoded function bindings or arbitrary SQL generation.

---

## Architecture Flow

```
User CLI (app/main.py)
         │
         ▼
Gemini MCP Agent (app/agent.py)  ◄───► Google Gemini (gemini-3.5-flash-lite)
         │
         ▼ (MCP stdio JSON-RPC protocol)
FastMCP Server (mcp_server/server.py)
   ├── @mcp.tool() get_financial_data
   ├── @mcp.tool() get_org_summary
   ├── @mcp.tool() compare_forecast
   ├── @mcp.tool() get_top_variances
   ├── @mcp.tool() convert_financial_month
   ├── @mcp.tool() convert_calendar_to_financial
   └── @mcp.tool() convert_financial_quarter
         │
         ▼ (PostgreSQL Parameterized Queries)
   Docker PostgreSQL Container (finance-postgres)
   Database: mydatabase | Table: financial_forecasts (30 records)
```

### Layer Breakdown

1. **User / CLI Interface ([`app/main.py`](app/main.py))**: Interactive CLI loop where users ask questions in natural language.
2. **Gemini MCP Agent ([`app/agent.py`](app/agent.py))**: Powered by `gemini-3.5-flash-lite`. Connects to FastMCP over `stdio`, dynamically discovers available tools via `session.list_tools()`, and orchestrates multi-turn tool calling through `session.call_tool()`.
3. **FastMCP Server ([`mcp_server/server.py`](mcp_server/server.py))**: Hosts all 7 financial and calendar conversion tools decorated with `@mcp.tool()`.
4. **Financial Year Skill ([`app/skills/financial_year.py`](app/skills/financial_year.py))**: Deterministically translates Indian financial year/month/quarter notation to calendar dates.
5. **PostgreSQL Client ([`app/database.py`](app/database.py))**: Manages database connections via `psycopg` (v3) with 3-second connection timeouts and executes parameterized SQL queries without concatenating raw user input.
6. **Docker PostgreSQL Container (`finance-postgres`)**: Live database holding the `financial_forecasts` table with 30 dummy records.

---

## 1. Prerequisites

- **Python 3.10+** (Python 3.12 recommended)
- **Docker Desktop** (with the `finance-postgres` container running)
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

## 2. Quickstart Setup

### Step 1: Clone Repository & Create Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Edit `.env` and provide your credentials:
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mydatabase
DATABASE_USER=postgres
DATABASE_PASSWORD=Harshul01

GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

---

## 3. Database Setup (Docker PostgreSQL)

### Step 1: Start PostgreSQL Container
```powershell
docker run --name finance-postgres -e POSTGRES_PASSWORD=Harshul01 -e POSTGRES_DB=mydatabase -p 5432:5432 -d postgres:latest
```

### Step 2: Seed Database
```powershell
Get-Content finance_dump.sql | docker exec -i finance-postgres psql -U postgres -d mydatabase
```

---

## 4. Running the Application

### Option A: Interactive AI Agent CLI (Recommended)
```powershell
python -m app.main
```

**Example queries you can ask:**
- `"What is Q1 FY2025-26?"`
- `"What is the actual value for ORG001 in January 2026?"`
- `"Tell me the actual value of 10th month of fy2025-2026 for org001"`
- `"Give me an overall summary for ORG003"`
- `"Which organization has the largest variance between forecast and actual?"`

### Option B: Standalone MCP Server Test Client (No AI required)
```powershell
python mcp_server/test_client.py
```

---

## 5. Running Automated Tests

Run the complete test suite (59 automated unit and integration tests):

```powershell
python -m pytest
```

---

## 6. Project Structure

```text
├── app/
│   ├── __init__.py
│   ├── agent.py                 # Gemini AI Agent with FastMCP client integration
│   ├── database.py              # psycopg (v3) PostgreSQL client with safe timeouts
│   ├── main.py                  # Interactive CLI entrypoint
│   ├── tools.py                 # Core financial query business logic
│   └── skills/
│       ├── __init__.py
│       └── financial_year.py    # Deterministic Indian FY date converter
├── mcp_server/
│   ├── server.py                # FastMCP server with @mcp.tool() decorators
│   └── test_client.py           # CLI MCP test client
├── tests/
│   ├── test_agent.py            # Agent configuration & tool registry tests
│   ├── test_financial_year.py   # 40 comprehensive Indian FY unit tests
│   ├── test_mcp_agent.py        # FastMCP server & MCP Agent integration tests
│   └── test_tools.py            # Database tools integration tests
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules for secrets, virtualenvs & caches
├── finance_dump.sql             # SQL dump containing 30 seed records
├── pytest.ini                   # Pytest configuration
├── README.md                    # Project documentation
└── requirements.txt             # Python dependencies
```

---

## License
MIT
