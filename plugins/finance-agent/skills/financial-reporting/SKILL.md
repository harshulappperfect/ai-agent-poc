---
name: financial-reporting
description: Guidelines for generating multi-table executive summary reports, department budget overviews, and organizational performance metrics.
---

# Financial Reporting Skill

Use this skill when generating summary reports or executive overviews for stakeholders across the 9 relational tables.

## Executive Reporting Standards
- Always format currency values rounded to 2 decimal places (e.g. `150,250.00`).
- Explicitly identify Organization names/IDs, Department codes, and Fiscal/Calendar periods.
- Provide a brief verbal narrative highlighting key takeaways alongside markdown tables.

## Common Report Types
- **Department Budget Utilization**: JOIN `departments`, `budgets`, and `invoices`/`transactions`.
- **Vendor Category Spend Analysis**: JOIN `vendors` and `invoices` aggregated by `category`.
- **Project Budget Health**: JOIN `projects` and `departments` comparing project budgets to spent amounts.
- **Organization Financial Summary**: Use `get_org_summary` or query `financial_forecasts`.
