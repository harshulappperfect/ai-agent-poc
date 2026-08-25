# Indian Financial Year & Month Conversion Skill

This skill provides the standard rules, conversion logic, and interpretation guidelines for translating between **Indian Financial Years / Months** and **Normal Calendar Years / Months**.

---

## 1. Indian Financial Year Definition

In India, the official Financial Year (FY) / Fiscal Year runs from **April 1** of one calendar year to **March 31** of the following calendar year.

- **Start Date**: April 1 (Calendar Month 4)
- **End Date**: March 31 of next year (Calendar Month 3)
- **Duration**: Exactly 12 months across 2 calendar years.

---

## 2. Financial Month Numbering Scheme

The months of an Indian Financial Year are numbered chronologically from 1 to 12 starting in April:

| FY Month Number | Calendar Month | Calendar Month Number | Year Offset from FY Start |
| :--- | :--- | :--- | :--- |
| **FY Month 1** | April | 4 | +0 (Start Year) |
| **FY Month 2** | May | 5 | +0 (Start Year) |
| **FY Month 3** | June | 6 | +0 (Start Year) |
| **FY Month 4** | July | 7 | +0 (Start Year) |
| **FY Month 5** | August | 8 | +0 (Start Year) |
| **FY Month 6** | September | 9 | +0 (Start Year) |
| **FY Month 7** | October | 10 | +0 (Start Year) |
| **FY Month 8** | November | 11 | +0 (Start Year) |
| **FY Month 9** | December | 12 | +0 (Start Year) |
| **FY Month 10** | January | 1 | +1 (Next Year) |
| **FY Month 11** | February | 2 | +1 (Next Year) |
| **FY Month 12** | March | 3 | +1 (Next Year) |

---

## 3. Financial Quarters

An Indian Financial Year is divided into 4 quarters:

| Quarter | FY Months | Calendar Months Covered | Example for FY 2025-26 |
| :--- | :--- | :--- | :--- |
| **Q1** | Month 1, 2, 3 | April, May, June | April 2025 – June 2025 |
| **Q2** | Month 4, 5, 6 | July, August, September | July 2025 – September 2025 |
| **Q3** | Month 7, 8, 9 | October, November, December | October 2025 – December 2025 |
| **Q4** | Month 10, 11, 12 | January, February, March | January 2026 – March 2026 |

---

## 4. Conversion Formulas

### A. Calendar Month & Year to Financial Year
Given a calendar `year` and `month` (1 to 12):

$$\text{FY Start Year} = \begin{cases} \text{year}, & \text{if } \text{month} \ge 4 \\ \text{year} - 1, & \text{if } \text{month} \le 3 \end{cases}$$

$$\text{FY Notation} = \text{"FY" } + \text{FY Start Year} + \text{"-"} + (\text{FY Start Year} + 1 \pmod{100})$$

**Examples:**
- `(2025, 4)` (April 2025) $\rightarrow$ Start Year = 2025 $\rightarrow$ `FY2025-26`
- `(2025, 12)` (December 2025) $\rightarrow$ Start Year = 2025 $\rightarrow$ `FY2025-26`
- `(2026, 1)` (January 2026) $\rightarrow$ Start Year = 2025 $\rightarrow$ `FY2025-26`
- `(2026, 3)` (March 2026) $\rightarrow$ Start Year = 2025 $\rightarrow$ `FY2025-26`
- `(2026, 4)` (April 2026) $\rightarrow$ Start Year = 2026 $\rightarrow$ `FY2026-27`

---

### B. Calendar Month to Financial Month Number
Given a calendar `month` (1 to 12):

$$\text{FY Month} = \begin{cases} \text{month} - 3, & \text{if } 4 \le \text{month} \le 12 \\ \text{month} + 9, & \text{if } 1 \le \text{month} \le 3 \end{cases}$$

**Examples:**
- April (month 4): $4 - 3 = 1$
- December (month 12): $12 - 3 = 9$
- January (month 1): $1 + 9 = 10$
- March (month 3): $3 + 9 = 12$

---

### C. Financial Year & Financial Month to Calendar Month & Year
Given a financial year start year $Y_{\text{start}}$ and financial month $M_{\text{fy}}$ ($1 \le M_{\text{fy}} \le 12$):

$$\text{Calendar Month} = \begin{cases} M_{\text{fy}} + 3, & \text{if } 1 \le M_{\text{fy}} \le 9 \\ M_{\text{fy}} - 9, & \text{if } 10 \le M_{\text{fy}} \le 12 \end{cases}$$

$$\text{Calendar Year} = \begin{cases} Y_{\text{start}}, & \text{if } 1 \le M_{\text{fy}} \le 9 \\ Y_{\text{start}} + 1, & \text{if } 10 \le M_{\text{fy}} \le 12 \end{cases}$$

**Examples:**
- `FY2025-26` (Start Year 2025), Month 1 $\rightarrow$ Month $1+3 = 4$ (April), Year 2025 $\rightarrow$ **April 2025** (`2025-04`)
- `FY2025-26` (Start Year 2025), Month 6 $\rightarrow$ Month $6+3 = 9$ (September), Year 2025 $\rightarrow$ **September 2025** (`2025-09`)
- `FY2025-26` (Start Year 2025), Month 9 $\rightarrow$ Month $9+3 = 12$ (December), Year 2025 $\rightarrow$ **December 2025** (`2025-12`)
- `FY2025-26` (Start Year 2025), Month 10 $\rightarrow$ Month $10-9 = 1$ (January), Year $2025+1 = 2026$ $\rightarrow$ **January 2026** (`2026-01`)
- `FY2025-26` (Start Year 2025), Month 12 $\rightarrow$ Month $12-9 = 3$ (March), Year $2025+1 = 2026$ $\rightarrow$ **March 2026** (`2026-03`)

---

## 5. Supported FY Notation Formats

The parser recognizes standard variations of Indian financial year expressions:

1. **Standard Full**: `FY2025-26`, `FY 2025-26`, `FY2025-2026`, `FY 2025-2026`
2. **Short Year**: `FY25-26`, `FY 25-26`, `25-26`
3. **Descriptive**: `2025-26 financial year`, `financial year 2025-26`, `fiscal year 2025-26`
4. **Single-Year References**:
   - `financial year 2025` / `2025` $\rightarrow$ Start Year 2025 (`FY2025-26`)
   - `FY2026` / `FY26` $\rightarrow$ Evaluated as financial year ending in 2026 (`FY2025-26`) or starting year 2026 (`FY2026-27`) based on standard fiscal conventions.
5. **Quarterly References**: `Q1 FY2025-26`, `Q2 2025-26`, `Q4 FY26`
6. **Month References**: `financial month 10`, `FY month 4`, `month 12 of FY2025-26`

---

## 6. Deterministic Agent Execution Flow

To ensure 100% accuracy and prevent LLM hallucination:

1. **User asks a question** mentioning financial year, fiscal year, FY, or financial month.
2. **Gemini Agent invokes the conversion tool** (`convert_financial_month` or `convert_financial_quarter`).
3. **Python Skill Module deterministically computes**:
   - `calendar_year`
   - `calendar_month`
   - `calendar_date_month` (`YYYY-MM`)
4. **Gemini Agent invokes the existing database tool** (`get_financial_data`, `compare_forecast`, etc.) passing `YYYY-MM`.
5. **PostgreSQL returns the exact record**.
6. **Gemini returns the grounded response** to the user.
