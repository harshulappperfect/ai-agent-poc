---
name: financial-analysis
description: Guidelines for multi-table financial analysis across budgets, actual forecasts, invoices, departments, vendors, and projects.
---

# Financial Analysis Skill

Use this skill when evaluating complex multi-table relational financial data across organizations, departments, vendors, projects, and employees.

## 9-Table Relational Schema
1. `organizations`: Core company entities (`id`, `name`, `code`, `country`).
2. `departments`: Functional divisions belonging to organizations (`id`, `org_id`, `name`, `code`).
3. `employees`: Staff members per department (`id`, `dept_id`, `name`, `email`, `role`, `salary`, `hire_date`).
4. `vendors`: External suppliers (`id`, `name`, `category`, `tax_id`).
5. `budgets`: Fiscal year allocated budgets (`id`, `dept_id`, `fiscal_year`, `allocated_amount`).
6. `financial_forecasts`: Forecast vs actual metrics (`id`, `org_id`, `month`, `forecast`, `actual`).
7. `invoices`: Supplier billing records (`id`, `vendor_id`, `dept_id`, `invoice_date`, `amount`, `status`).
8. `transactions`: Departmental ledger items (`id`, `invoice_date`, `dept_id`, `amount`, `transaction_type`).
9. `projects`: Departmental initiatives (`id`, `dept_id`, `name`, `budget`, `status`).

## Analysis Methodologies
- **Budget vs Actual Variance**: `allocated_amount - SUM(actual)` or `allocated_amount - SUM(invoices.amount)`
- **Net Forecast Variance**: `actual - forecast`
- **Vendor Spend Breakdown**: `SUM(invoices.amount)` grouped by `vendor_id` or `vendors.category`
- **Department Payroll Cost**: `SUM(employees.salary)` grouped by `dept_id`

## Tool Selection Guidelines
- For dynamic multi-table queries (`JOIN`, `GROUP BY`, `SUM`, `AVG`, CTEs), use `run_read_only_query`.
- For inspecting schema details or column data types, use `get_database_schema`.
- For converting Indian FY date notation to calendar dates ('YYYY-MM'), use `convert_financial_month` or `convert_financial_quarter`.
