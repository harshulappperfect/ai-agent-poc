---
name: financial-year
description: Instructions and deterministic rules for Indian Financial Year (FY), month (1-12), and quarter calendar conversions.
---

# Financial Year Conversion Skill

Use this skill when processing user queries containing Indian Financial Year (FY) terminology, month numbers, or quarters.

## Financial Year (FY) Convention
- An Indian Financial Year runs from October 1 to September 30.
- Financial Year Notation: "FY2025-26", "FY25-26", or "2025-26" refers to October 2025 – September 2026.

## Financial Month Mapping (1-12)
- FY Month 1 = October (Start of FY)
- FY Month 2 = November
- FY Month 3 = December
- FY Month 4 = January (Next Calendar Year)
- FY Month 5 = February
- FY Month 6 = March
- FY Month 7 = April
- FY Month 8 = May
- FY Month 9 = June
- FY Month 10 = July
- FY Month 11 = August
- FY Month 12 = September (End of FY)

## Quarters Mapping
- Q1 = FY Months 1-3 (October to December)
- Q2 = FY Months 4-6 (January to March)
- Q3 = FY Months 7-9 (April to June)
- Q4 = FY Months 10-12 (July to September)

## Workflow & Tool Usage Rules
1. When a query references financial year notation (e.g., 'FY2025-26', 'FY month 10', 'Q1 FY2025-26'):
   - Invoke `convert_financial_month`, `convert_financial_quarter`, or `convert_calendar_to_financial` first to obtain the exact calendar date (`YYYY-MM`).
   - Do NOT guess or hardcode date arithmetic manually.
2. Use the resulting `YYYY-MM` calendar string to call database tools (`get_financial_data`, `compare_forecast`).
