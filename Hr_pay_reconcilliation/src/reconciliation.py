# reconciliation.py
import duckdb
import logging
from enum import Enum
from validator import HRISRecord,PayrollRegister,FinanceLedger
from config import settings
from src import ingestion

db_path=settings.database_path
audit_logger=logging.getLogger("audit")
logger=logging.getLogger("pipeline")
conn=ingestion.get_connection(db_path)



class error_types(Enum):
    pass
    

# --- imports ---
# duckdb, logging, dataclass (or Pydantic model), Enum, settings

# --- 1. ERROR TYPES ---
# Enum (or constants) holding the 10 error type names.
# Why an Enum instead of raw strings? (typos fail loudly)

# --- 2. FINDING SHAPE ---
# One structure for every finding:
#   error_type, severity, employee_id, pay_period,
#   expected_value, actual_value, message
# Decide: which fields are nullable? (HEADCOUNT_MISMATCH has no employee)

# --- 3. THRESHOLDS ---
# Read from settings, never hardcode:
#   MoM variance %, OT limit, ESI wage boundary, amount tolerance
# Think: what tolerance do you allow when comparing two money values?

# --- 4. BUILD ALIGNED DATASET ---
def build_reconciliation_view(conn, pay_period):
    # Goal: one row per (employee, period) with E, P, G side by side.
    # Decide first: join keys? grain of each table? which table drives?
    # Decide: do you filter to one Pay_Period here or later?
    # Decide: FULL OUTER JOIN or simpler joins for some rules?
    # Output: a table/view/dataframe the rules below can read
    conn.execute("SELECT * FROM dim_employees WHERE Date_Of_Joining > ?",[pay_period])
    conn.execute("SELECT * FROM fact_payroll WHERE Pay_Period = ?",[pay_period])
    conn.execute("SELECT * FROM fact_gl WHERE Pay_Period=?",[pay_period])
    conn.execute("SELECT * FROM dim_employees AS e FULL OUTTER JOIN fact_payroll AS p USING Employee_ID ")
    return conn

# --- 5. RULES (one function each, same signature) ---
# Each: takes conn (and/or the aligned data) -> returns list of findings
# Rules must not modify data and must not depend on each other.

def check_terminated_paid(...):   # E.status vs P existing after leaving date
    pass

def check_orphan_payroll(...):    # P exists, E missing
    pass

def check_duplicate_payment(...): # same employee + period appears more than once. Why grouping?
    pass

def check_base_rate_mismatch(...):# E.Base_Salary_HRIS vs P.Base_Salary_Payroll
    pass

def check_mom_variance(...):      # needs previous period. How do you get it? (window fn or self-join)
    pass

def check_headcount_mismatch(...):# aggregate: compare counts across systems per period
    pass

def check_off_cycle_adjustment(...):  # define what "off-cycle" means in your data first
    pass

def check_gl_net_mismatch(...):   # P.Net_pay vs G posted amount. Beware: multiple GL rows per employee?
    pass

def check_esi_boundary(...):      # gross near the ESI limit: risk, not certain error
    pass

def check_ot_anomaly(...):        # overtime vs a rule you define (absolute? relative to base?)
    pass

# --- 6. RUNNER ---
def run_reconciliation(conn, pay_period):
    # 1. build the aligned view
    # 2. loop over the list of rule functions
    # 3. one rule failing must not stop the others (what do you log?)
    # 4. collect all findings
    # 5. persist findings (new table? what columns? re-run safe?)
    # 6. return a summary: counts per error type
    pass