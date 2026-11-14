# anomaly_detector.py
"""
Insight engine: statistical anomaly detection and cost pattern analysis.
Reads from DuckDB. Returns plain dicts/lists — no DB writes.
"""
import logging
import os
import duckdb
import pandas as pd
from config import settings
from src import ingestion
import numpy as np



def _get_logger():
    log = logging.getLogger("anomaly_detector")
    if not log.handlers:
        os.makedirs("logs", exist_ok=True)
        h = logging.FileHandler("logs/anomaly_detector.log")
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def _cfg(name, default):
    return getattr(settings, name, None) or default



# ------------------------------------------------------------------
# 1. OT HOTSPOTS — Z-score per department
# ------------------------------------------------------------------
def ot_hotspots_by_dept(conn, pay_period: str) -> list[dict]:
    """
    For each department, compute:
      - total OT this period
      - mean OT across all departments
      - Z-score = (dept_total - mean) / std_dev
    Return departments with Z-score above threshold (default 1.5).

    Returns list of dicts:
      { department, total_ot, mean_ot, z_score, pct_above_avg }
    """
    over_time=conn.execute("""
        SELECT Department,SUM(Overtime) AS total_ot 
        FROM fact_payroll
        WHERE pay_period =? AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment'
        Group By Department 
""",[pay_period]).fetchall()

    df = pd.DataFrame(over_time, columns=["department", "total_ot"])

    df["mean_ot"] = df["total_ot"].mean()
    df["std_ot"]  = df["total_ot"].std()
    df["z_score"] = (df["total_ot"] - df["mean_ot"]) / df["std_ot"]
    df["pct_above_avg"] = round((df["total_ot"] - df["mean_ot"]) / df["mean_ot"] * 100, 1)
    threshold = _cfg("ot_z_threshold", 1.5)
    df = df[df["z_score"] > threshold]
    

    return (df.to_dict("records"))
    

# ------------------------------------------------------------------
# 2. ESI BOUNDARY EMPLOYEES
# ------------------------------------------------------------------
def esi_boundary_employees(conn, pay_period: str) -> list[dict]:
    """
    Employees whose Gross_Pay is between (ESI_limit - band) and ESI_limit.
    Source: fact_payroll (not dim_employees — HRIS has no computed gross).

    Returns list of dicts:
      { employee_id, department, gross_pay, esi_limit, gap }
    """
    limit = float(_cfg("ESI_wage_boundary", 21000))
    band  = float(_cfg("ESI_band", 3000))
    limit_band=limit-band
    esi_boundary=conn.execute("""SELECT Employee_ID,Department,Gross_Pay 
            FROM fact_payroll
            WHERE pay_period =? AND Gross_Pay BETWEEN ? AND ?
            AND COALESCE (Payment_Mode,'') <> 'Manual_Adjustment'
            """,[pay_period,limit_band,limit]).fetchall()
    df=pd.DataFrame(esi_boundary, columns=["Employee_ID","Department","Gross_Pay"])
    df["gap"]= limit-df["Gross_Pay"]
    df["esi_limit"] = limit

    return (df.to_dict("records"))

    # Query fact_payroll:
    #   SELECT Employee_ID, Department, Gross_Pay
    #   WHERE Pay_Period = ? AND Gross_Pay BETWEEN (limit-band) AND limit
    #   AND Payment_Mode != 'Manual_Adjustment'
    
    # For each row add:  gap = limit - gross_pay
    
    # Return list of dicts
    
    


# ------------------------------------------------------------------
# 3. DEPARTMENT COST SUMMARY
# ------------------------------------------------------------------
def dept_cost_summary(conn, pay_period: str) -> list[dict]:
    """
    Per department: total gross, total net, total OT, headcount.
    Used for the bar chart on the Overview page.

    Returns list of dicts:
      { department, headcount, total_gross, total_net, total_ot }
    """
    dept=conn.execute("""SELECT Department,COUNT(DISTINCT Employee_ID) AS head_count,SUM(Gross_Pay) AS total_gross,SUM(Net_pay) AS total_net,SUM(Overtime) AS total_ot
            FROM fact_payroll
            WHERE pay_period=? AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment' 
            GROUP BY Department            
            """,[pay_period]).fetchall()
    df=pd.DataFrame(dept,columns=["Department","headcount","total_gross","total_net","total_ot"])
    return (df.to_dict("records"))
    # Query fact_payroll grouped by Department for this pay_period
    # SELECT Department,
    #        COUNT(DISTINCT Employee_ID) AS headcount,
    #        SUM(Gross_Pay) AS total_gross,
    #        SUM(Net_pay) AS total_net,
    #        SUM(Overtime) AS total_ot
    # GROUP BY Department
    
    


# ------------------------------------------------------------------
# 4. TOP COST-SAVING OBSERVATIONS
# ------------------------------------------------------------------
def top_observations(conn, pay_period: str, n: int = 5) -> list[str]:
    """
    Read fact_reconciliation for this period.
    Group by error_type, sum the 'actual' column (the amount at risk).
    Return top-n human-readable strings ranked by total amount.

    Example output:
      2 CRITICAL_TERMINATED_PAID findings — ₹77,600 total — recover immediately"
    """
    # Query fact_reconciliation WHERE pay_period = ?
    # For each error_type: count findings, sum(actual) where actual is not null
    # Sort by sum(actual) DESC, take top n
    # Format each as a string
    
    # Recommended action map (use this):
    ACTIONS = {
        "CRITICAL_TERMINATED_PAID":  "recover immediately",
        "ORPHAN_PAYROLL_RECORD":      "escalate to fraud review",
        "DUPLICATE_PAYMENT":          "hold second payment",
        "BASE_RATE_MISMATCH":         "check increment letter",
        "GL_NET_MISMATCH":            "correction journal entry",
        "MOM_VARIANCE":               "ask for reason",
        "OFF_CYCLE_MANUAL_ADJ":       "get retroactive approval",
        "OT_ANOMALY":                 "review shift roster",
        "ESI_BOUNDARY_RISK":          "monitor next cycle",
        "HEADCOUNT_MISMATCH":         "separate joiners from orphans",
    }
    observe=conn.execute("""SELECT error_type,SUM(actual) AS amount_at_risk,COUNT(*) AS finding_count,message 
                    FROM fact_reconciliation 
                    WHERE pay_period = ? AND actual IS NOT NULL 
                    GROUP BY  error_type 
                    ORDER BY SUM(actual) DESC
            """,[pay_period]).fetchall()
    df=pd.DataFrame(observe,columns=["error_type","amount_at_risk","finding_count","message"])
    observations = []
    for _,row in df.head(15).iterrows():
        action = ACTIONS.get(row["error_type"], "review manually")
        line = f"{row['finding_count']} findings in {action} ₹{row['amount_at_risk']:,.0f} total"
        observations.append(line)
    return observations
    
    


# ------------------------------------------------------------------
# 5. RISK RANKING — ordered list for the drilldown page
# ------------------------------------------------------------------
def risk_ranked_findings(conn, pay_period: str) -> list[dict]:
    """
    Read fact_reconciliation, return all findings for this period
    sorted by: severity (CRITICAL first), then actual amount desc.

    Returns list of dicts matching fact_reconciliation columns.
    """
    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    # Query fact_reconciliation WHERE pay_period = ?
    # Load into DataFrame
    # Map severity to sort key using SEVERITY_ORDER
    # Sort by (severity_rank ASC, actual DESC)
    # Return as list of dicts
    
    pass


# ------------------------------------------------------------------
# RUNNER
# ------------------------------------------------------------------
def run_insights(conn, pay_period: str) -> dict:
    """
    Run all five analyses. Returns a single dict with all results.
    One analysis failing must not stop the others.
    """
    log = _get_logger()
    log.info("Insight engine begin for %s", pay_period)
    
    results = {}
    tasks = {
        "ot_hotspots":    lambda: ot_hotspots_by_dept(conn, pay_period),
        "esi_boundary":   lambda: esi_boundary_employees(conn, pay_period),
        "dept_costs":     lambda: dept_cost_summary(conn, pay_period),
        "observations":   lambda: top_observations(conn, pay_period),
        "risk_ranked":    lambda: risk_ranked_findings(conn, pay_period),
    }
    
    for name, fn in tasks.items():
        try:
            results[name] = fn()
            log.info("%s complete", name)
        except Exception:
            log.exception("%s failed", name)
            results[name] = []
    
    return results