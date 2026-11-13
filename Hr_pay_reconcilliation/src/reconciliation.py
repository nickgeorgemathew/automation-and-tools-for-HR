# reconciliation.py
import duckdb
from dataclasses import dataclass
import logging
from enum import Enum
from config import settings
from src import ingestion
from Schema_validator import HRISRecord,PayrollRegister,FinanceLedger



reconciliation_logger = logging.getLogger("reconciliation")
reconciliation_logger.setLevel(logging.INFO)
a_handler = logging.FileHandler("logs/reconciliation.log")
a_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
reconciliation_logger.addHandler(a_handler)

#getting connection for the database
db_path=settings.database_path
conn=ingestion.get_connection(db_path)



class ErrorType(Enum):
    ORPHAN_PAYROLL_RECORD="ORPHAN_PAYROLL_RECORD"
    CRITICAL_TERMINATED_PAID="CRITICAL_TERMINATED_PAID"
    BASE_RATE_MISMATCH="BASE_RATE_MISMATCH"
    GL_NET_MISMATCH="GL_NET_MISMATCH"
    ESI_BOUNDARY_RISK="ESI_BOUNDARY_RISK"
    OT_ANOMALY="OT_ANOMALY"
    DUPLICATE_PAYMENT="DUPLICATE_PAYMENT"
    MOM_VARIANCE="MOM_VARIANCE"
    HEADCOUNT_MISMATCH="HEADCOUNT_MISMATCH"
    OFF_CYCLE_MANUAL_ADJ="OFF_CYCLE_MANUAL_ADJ"




    
@dataclass
class Finding:
    error_type: ErrorType
    severity: str
    employee_id: str | None      # None allowed (headcount has no employee)
    pay_period: str
    expected: float | None
    actual: float | None
    message: str

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
    # Pass the parameter three times—once for each placeholder in the unified query
    query = """
    SELECT * 
    FROM (SELECT * FROM dim_employees WHERE Date_Of_Joining <= ? AND (Date_Of_Leaving IS NULL OR Date_of_Leaving > ?)) AS e 
    FULL OUTER JOIN (SELECT * FROM fact_payroll WHERE Pay_Period = ?) AS p 
        USING (Employee_ID)
    LEFT JOIN (SELECT * FROM fact_gl WHERE Pay_Period = ?) AS g 
        USING (Employee_ID)
"""
    # Execute all at once, passing the parameter for each '?' positional placeholder
    try:
        result = conn.execute(query, [pay_period, pay_period, pay_period,pay_period]).fetchall()
        return conn,result
    except Exception as e:
        print(f"error:{e}") 
        reconciliation_logger.error(f"{e}") 

# --- 5. RULES (one function each, same signature) ---
# Each: takes conn (and/or the aligned data) -> returns list of findings
# Rules must not modify data and must not depend on each other.

def check_terminated_paid(conn,pay_period):   # E.status vs P existing after leaving date
    rows = conn.execute("""
            SELECT e.Employee_ID,p.Net_Pay  FROM dim_employees AS e JOIN fact_payroll AS p ON e.Employee_ID = p.Employee_ID  WHERE p.Pay_period =? AND  p.Pay_Period > e.Date_of_Leaving AND e.Date_of_Leaving IS NOT Null
        """, [pay_period]).fetchall()
    findings=[Finding(ErrorType.CRITICAL_TERMINATED_PAID, "CRITICAL", emp, pay_period,
                        None, net, f"{emp} has exited but has been paid")for emp, net in rows]
    reconciliation_logger.critical(f"{findings}")
    
    return findings


def check_orphan_payroll(conn,pay_period):    # P exists, E missing
    rows = conn.execute("""
            SELECT p.Employee_ID, p.Net_pay
            FROM fact_payroll p
            LEFT JOIN dim_employees e ON e.Employee_ID = p.Employee_ID
            WHERE p.Pay_Period = ? AND e.Employee_ID IS NULL
        """, [pay_period]).fetchall()
    
    return [
            Finding(ErrorType.ORPHAN_PAYROLL_RECORD, "HIGH", emp, pay_period,
                    None, net, f"{emp} was paid but does not exist in HRIS")
            for emp, net in rows
        ]
    

def check_duplicate_payment(conn,pay_period): # same employee + period appears more than once. Why grouping?
    rows = conn.execute("""
            SELECT e.Employee_ID,Count(*)
            FROM fact_payroll p
            JOIN dim_employees e
            ON e.Employee_ID =p.Employee_ID
            WHERE Pay_Period =?
            GROUP BY e.Employee_ID
            Having Count(*)>1

        """, [pay_period]).fetchall()
    
    return [
            Finding(ErrorType.DUPLICATE_PAYMENT, severity="HIGH", employee_id=emp, pay_period=pay_period,expected=None,actual=None,message=
                    f"Employee {emp} was paid {count} times in {pay_period} )"
            )
            for emp, count in rows
        ]
    

def check_base_rate_mismatch(conn,pay_period):# E.Base_Salary_HRIS vs P.Base_Salary_Payroll
    rows = conn.execute("""
            SELECT p.Employee_ID, e.Base_Salary_HRIS, p.Base_Salary_Payroll
            FROM fact_payroll p
            JOIN dim_employees e ON e.Employee_ID = p.Employee_ID
            WHERE p.Pay_Period = ?
              AND ABS(e.Base_Salary_HRIS - p.Base_Salary_Payroll) > ?
        """, [pay_period, settings.tolerance]).fetchall()
    
    return [
            Finding(ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pay_period,
                    hris, payroll, f"HRIS says {hris}, payroll used {payroll}")
            for emp, hris, payroll in rows
        ]
    

def check_mom_variance(
    conn, pay_period: str, threshold_pct: float = 0.15
) -> list[Finding]:
  rows = conn.execute(
      """
        WITH monthly_totals AS (
            -- Step 1: Aggregate pay per employee per period in case of multiple runs
            SELECT 
                Employee_ID,
                Pay_Period,
                SUM(Gross_Pay) AS current_pay
            FROM fact_payroll
            GROUP BY Employee_ID, Pay_Period
        ),
        mom_comparison AS (
            -- Step 2: Look back 1 period per employee using LAG()
            SELECT 
                Employee_ID,
                Pay_Period,
                current_pay,
                LAG(current_pay) OVER (
                    PARTITION BY Employee_ID 
                    ORDER BY Pay_Period
                ) AS prev_pay
            FROM monthly_totals
        )
        -- Step 3: Filter to the target pay_period and flag large swings
        SELECT 
            Employee_ID,
            prev_pay,
            current_pay,
            ROUND(((current_pay - prev_pay) / prev_pay) * 100, 2) AS pct_change
        FROM mom_comparison
        WHERE Pay_Period = ?
          AND prev_pay IS NOT NULL
          AND prev_pay > 0
          AND ABS(current_pay - prev_pay) / prev_pay > ?
    """,
      [pay_period, threshold_pct],
  ).fetchall()

  return [
      Finding(
          error_type=ErrorType.MOM_VARIANCE,
          severity="MEDIUM",
          employee_id=emp,
          pay_period=pay_period,
          expected=prev_pay,
          actual=curr_pay,
          message=(
              f"MoM Gross Pay changed by {pct}% (Previous: {prev_pay}, Current:"
              f" {curr_pay})"
          ),
      )
      for emp, prev_pay, curr_pay, pct in rows
  ]
    

def check_headcount_mismatch(conn,pay_period):# aggregate: compare counts across systems per period
    rows = conn.execute(
        """
        SELECT COUNT(*) FROM
        dim_employees AS e 
        JOIN Fact_payroll AS p ON p.Employee_ID = e.Employee_ID
        WHERE DISTINCT Employee_ID AND Pay_Period = ?
    """,
        [pay_period]
    ).fetchall()
    
    return [
        Finding(
            error_type=ErrorType.HEADCOUNT_MISMATCH,
            severity="MEDIUM",
            employee_id=emp,
            pay_period=pay_period,
            expected=count,
            actual=found,
            message=(f"""
            emp_id {emp} found {count} times
""")
        )for emp,count,found in rows
        
    ]
    

def check_off_cycle_adjustment(conn,pay_period):  # define what "off-cycle" means in your data first
    rows = conn.execute("""
        SELECT * FROM 
        """, [pay_period, settings.tolerance]).fetchall()
    
    return [
            Finding(ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pay_period,
                    hris, payroll, f"HRIS says {hris}, payroll used {payroll}")
            for emp, hris, payroll in rows
        ]
    

def check_gl_net_mismatch(conn,pay_period):   # P.Net_pay vs G posted amount. Beware: multiple GL rows per employee?
    rows = conn.execute("""
        SELECT * FROM 
        """, [pay_period, settings.tolerance]).fetchall()
    
    return [
            Finding(ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pay_period,
                    hris, payroll, f"HRIS says {hris}, payroll used {payroll}")
            for emp, hris, payroll in rows
        ]

def check_esi_boundary(conn,pay_period):      # gross near the ESI limit: risk, not certain error
    rows = conn.execute("""
        SELECT Gross_Pay,ESI_Deduction FROM dim_employee Where Gross_pay > ? AND 
        """, [settings.esi_boundary,pay_period]).fetchall()
    
    return [
            Finding(ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pay_period,
                    hris, payroll, f"HRIS says {hris}, payroll used {payroll}")
            for emp, hris, payroll in rows
        ]

def check_ot_anomaly(conn,pay_period):        # overtime vs a rule you define (absolute? relative to base?)
    rows = conn.execute("""
        SELECT * FROM 
        """, [pay_period, settings.tolerance]).fetchall()
    
    return [
            Finding(ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pay_period,
                    hris, payroll, f"HRIS says {hris}, payroll used {payroll}")
            for emp, hris, payroll in rows
        ]



# Rule 1: presence ("in P but not in E")


# Rule 2: two systems disagree on a number


# Rule 3: aggregate GL FIRST, then LEFT JOIN (avoids row multiplication)


# Runner: same signature for every rule, so it's just a loop
RULES = [check_orphan_payroll, check_base_rate_mismatch, check_gl_net_mismatch,check_terminated_paid,check_duplicate_payment,check_mom_variance,check_headcount_mismatch,check_off_cycle_adjustment,check_esi_boundary,check_ot_anomaly]

def run_reconciliation(conn, pay_period):
    # 1. build the aligned view
    # 2. loop over the list of rule functions
    # 3. one rule failing must not stop the others (what do you log?)
    # 4. collect all findings
    # 5. persist findings (new table? what columns? re-run safe?)
    # 6. return a summary: counts per error type
    reconciliation_logger.info("Reconciliation Begin")
    findings = []
    for rule in RULES:
        try:
            findings += rule(conn, pay_period)
        except Exception:
            reconciliation_logger.exception("Rule %s failed", rule.__name__)  # full traceback
    return findings