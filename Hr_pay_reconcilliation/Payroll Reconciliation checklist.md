Good move — having a full map before continuing is smart, not avoidance.

---

## Full Project Checklist

---

### Part A — Foundation ✓ (mostly done)

- [x] `mock_generator.py` — 3 CSVs with injected faults
- [x] `validator.py` — column checks, Pydantic schema, quarantine
- [x] `ingestion.py` — MD5 dedup, DuckDB load, transaction, audit log
- [x] `Schema_validator.py` — Pydantic models for all 3 feeds
- [ ] Fix `build_reconciliation_view` SQL (3 issues identified last session)
- [ ] `test_validator.py` — write after reconciliation is working

---

### Part B — Reconciliation Engine (you are here)

**Step 1 — Fix `build_reconciliation_view`**
- [ ] Change `Date_Of_Joining > ?` to `Date_Of_Joining <= ?` (employees active by pay period)
- [ ] Change `Date_Of_Leaving = NULL` to `Date_Of_Leaving IS NULL`
- [ ] Change last `JOIN` to `FULL OUTER JOIN`

**Step 2 — Finish the 5 stub functions**
- [ ] `check_duplicate_payment` — GROUP BY Employee_ID + Pay_Period, HAVING COUNT > 1
- [ ] `check_mom_variance` — self-join or LAG window function on previous Pay_Period
- [ ] `check_headcount_mismatch` — COUNT(DISTINCT) across all 3 tables, compare
- [ ] `check_off_cycle_adjustment` — WHERE Payment_Mode = 'Manual_Adjustment'
- [ ] `check_gl_net_mismatch` — SUM GL per employee first, then compare to Net_pay

**Step 3 — Fix existing functions**
- [ ] `check_terminated_paid` — unpack row tuple correctly (6 fields, but list comp uses `emp, net`)
- [ ] `check_mom_variance` — still uses wrong ErrorType and wrong variables (copy-paste from base_rate)
- [ ] Remove duplicate `check_base_rate_mismatch` definition at line 173

**Step 4 — Wire the runner**
- [ ] Add all 10 rule functions to `RULES` list
- [ ] `run_reconciliation` — call `build_reconciliation_view`, pass result to rules that need it
- [ ] Add `findings` persistence: `CREATE TABLE IF NOT EXISTS fact_reconciliation(...)` in `setup_tables`
- [ ] Insert findings into `fact_reconciliation` after the rule loop

---

### Part C — Insight Engine

- [ ] Create `insight_engine.py`
- [ ] `ot_zscore_by_dept` — pandas groupby department, compute Z-score on Overtime column
- [ ] `esi_boundary_list` — WHERE Gross_Pay BETWEEN 18000 AND 21000
- [ ] `dept_cost_summary` — SUM by Department, compare to previous period
- [ ] `top_observations` — ranked list from findings + cost data
- [ ] `risk_rank_findings` — sort by severity then amount

---

### Part D — Streamlit Dashboard (`app.py`)

Build pages in this order (drilldown first, it's the most useful):

- [ ] **Page 2 — Mismatch Drilldown**
  - [ ] Load findings from `fact_reconciliation`
  - [ ] Filter widgets: Department, Error Type, Amount ≥
  - [ ] Table of flagged rows with severity color
  - [ ] "Mark Resolved" button that writes to `resolutions` table
  - [ ] Export to CSV button

- [ ] **Page 1 — Monthly Overview**
  - [ ] KPI tiles: Total Payroll, Headcount, Flagged Amount, Critical Flags, PF Liability
  - [ ] Bar chart: dept-wise spend
  - [ ] Donut chart: pay component mix

- [ ] **Page 4 — Audit Trail**
  - [ ] Table of reconciliation run history from `ingestion_audit`
  - [ ] Export audit report button

- [ ] **Page 3 — Cost Intelligence**
  - [ ] OT hotspots by department
  - [ ] ESI boundary employee list
  - [ ] Top 5 cost observations from insight engine

---

### Part E — Tests + Ship

- [ ] `test_validator.py`
  - [ ] Test valid file passes
  - [ ] Test missing column quarantines file
  - [ ] Test unknown feedtype returns False
  - [ ] Test bad row (invalid Employee_ID) goes to invalid_rows

- [ ] `test_reconciliation.py`
  - [ ] Load mock data with known injected faults
  - [ ] Assert `CRITICAL_TERMINATED_PAID` is found
  - [ ] Assert `ORPHAN_PAYROLL_RECORD` is found
  - [ ] Assert no false positives on clean rows

- [ ] `README.md` — architecture diagram, how to run, what it checks
- [ ] `requirements.txt` — confirm all imports are listed
- [ ] GitHub — push, confirm CI runs tests

---

**Where you are right now:** Step 1 of Part B — fix the 3 SQL bugs in `build_reconciliation_view`.

Do that first and paste back.