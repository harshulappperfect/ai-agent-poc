# Finance Agent Plugin

A shareable, self-contained Agent Plugin providing **Model Context Protocol (MCP)** tools and **Agent Skills** for financial data analysis, forecast comparisons, and Indian Financial Year date conversions.

## Plugin Structure

```text
plugins/finance-agent/
├── plugin.json               # Plugin manifest
├── mcp_config.json           # Standard MCP server registration
├── requirements.txt          # Isolated plugin dependencies
├── README.md                 # Plugin documentation
├── server/                   # FastMCP executable server
│   ├── database.py           # PostgreSQL psycopg (v3) client
│   ├── financial_year.py     # Deterministic FY date math engine
│   ├── tools.py              # Financial query business tools
│   └── server.py             # FastMCP stdio server
└── skills/                   # Agent Skills (Prompt & Reasoning Instructions)
    ├── financial-year/
    │   └── SKILL.md          # FY convention rules (Oct-Sep)
    ├── financial-analysis/
    │   └── SKILL.md          # Variance & performance formulas
    └── financial-reporting/
        └── SKILL.md          # Summary formatting guidelines
