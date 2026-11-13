# reconciliation.py
"""
Three-way payroll reconciliation (HRIS <-> Payroll <-> GL).

Every rule has the same signature:  rule(conn, pay_period) -> list[Finding]
Rules only read data. Nothing runs at import time (no DB connection, no log
file) so the module is safe to import from tests and from the Streamlit app.

pay_period is the first day of the month: "2024-10-01" (a date also works,
and "2024-10" is accepted).
"""
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

import duckdb

from config import settings


# --------------------------------------------------------------------------
# Logging (created lazily, so importing this module has no side effects)
# --------------------------------------------------------------------------
def _get_logger() -> logging.Logger:
    log = logging.getLogger("reconciliation")
    if not log.handlers:
        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/reconciliation.log")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


# --------------------------------------------------------------------------
# Thresholds: read from settings, fall back to a sane default if unset/zero.
# (settings.py currently holds 0 for several of these; 0 is never a useful
# threshold, so "unset or 0" means "use the default".)
# --------------------------------------------------------------------------
def _cfg(name: str, default):
    return getattr(settings, name, None) or default


def _tolerance() -> float:
    return _cfg("amount_tolerance", None) or _cfg("tolerance", 0.1)


# Statuses that mean "money did not actually leave the bank".
FAILED_STATUSES = ("FAILED", "REJECTED", "REVERSED")


class ErrorType(Enum):
    ORPHAN_PAYROLL_RECORD = "ORPHAN_PAYROLL_RECORD"
    CRITICAL_TERMINATED_PAID = "CRITICAL_TERMINATED_PAID"
    BASE_RATE_MISMATCH = "BASE_RATE_MISMATCH"
    GL_NET_MISMATCH = "GL_NET_MISMATCH"
    ESI_BOUNDARY_RISK = "ESI_BOUNDARY_RISK"
    OT_ANOMALY = "OT_ANOMALY"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    MOM_VARIANCE = "MOM_VARIANCE"
    HEADCOUNT_MISMATCH = "HEADCOUNT_MISMATCH"
    OFF_CYCLE_MANUAL_ADJ = "OFF_CYCLE_MANUAL_ADJ"


@dataclass
class Finding:
    error_type: ErrorType
    severity: str
    employee_id: str | None  # None allowed (headcount has no employee)
    pay_period: str
    expected: float | None
    actual: float | None
    message: str


def _norm_period(pay_period) -> str:
    """Return 'YYYY-MM-DD' for a str / date / datetime / 'YYYY-MM'."""
    if isinstance(pay_period, (date, datetime)):
        return pay_period.strftime("%Y-%m-%d")
    s = str(pay_period).strip()
    if len(s) == 7:  # 'YYYY-MM'
        s += "-01"
    return s[:10]


def _prev_period(pay_period: str) -> str:
    first = date.fromisoformat(pay_period)
    return (first.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()


# --------------------------------------------------------------------------
# Aligned view (one row per employee for the period) -- for the dashboard.
# Rules do NOT depend on it; each rule queries the base tables itself.
#
# Fixes vs the old version:
#   * HRIS is NOT filtered before the join (that manufactured fake orphans);
#     "active in period" is a flag column instead.
#   * Payroll and GL are aggregated to one row per employee BEFORE joining,
#     so duplicate / split rows cannot multiply the result.
#   * both joins are FULL OUTER, so GL-only and payroll-only people survive.
# --------------------------------------------------------------------------
def build_reconciliation_view(conn, pay_period):
    pp = _norm_period(pay_period)
    query = """
    WITH e AS (
        SELECT *,
               (Date_Of_Joining <= last_day(CAST(? AS DATE))
                AND (Date_Of_Leaving IS NULL
                     OR Date_Of_Leaving >= CAST(? AS DATE))) AS active_in_period
        FROM dim_employees
    ),
    p AS (
        SELECT Employee_ID,
               SUM(Net_pay)   AS payroll_net,
               SUM(Gross_Pay) AS payroll_gross,
               COUNT(*)       AS payroll_rows
        FROM fact_payroll
        WHERE Pay_Period = CAST(? AS DATE)
        GROUP BY Employee_ID
    ),
    g AS (
        SELECT Employee_ID,
               SUM(GL_Amount_Posted) AS gl_net,
               COUNT(*)              AS gl_rows
        FROM fact_gl
        WHERE Pay_Period = CAST(? AS DATE)
        GROUP BY Employee_ID
    )
    SELECT COALESCE(e.Employee_ID, p.Employee_ID, g.Employee_ID) AS Employee_ID,
           e.Employee_Name, e.Department, e.Employment_Status,
           e.Date_Of_Leaving, e.Base_Salary_HRIS, e.active_in_period,
           p.payroll_net, p.payroll_gross, p.payroll_rows,
           g.gl_net, g.gl_rows
    FROM e
    FULL OUTER JOIN p ON e.Employee_ID = p.Employee_ID
    FULL OUTER JOIN g ON COALESCE(e.Employee_ID, p.Employee_ID) = g.Employee_ID
    """
    try:
        return conn.execute(query, [pp, pp, pp, pp]).df()
    except Exception:
        _get_logger().exception("build_reconciliation_view failed")
        raise


# --------------------------------------------------------------------------
# RULES
# --------------------------------------------------------------------------
def check_terminated_paid(conn, pay_period):
    """Paid for a period that STARTS after the employee's leaving date.
    Someone who leaves on the 15th is legitimately paid for that month."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        SELECT p.Employee_ID, SUM(p.Net_pay), MAX(e.Date_Of_Leaving)
        FROM fact_payroll p
        JOIN dim_employees e ON e.Employee_ID = p.Employee_ID
        WHERE p.Pay_Period = CAST(? AS DATE)
          AND e.Date_Of_Leaving < CAST(? AS DATE)
          AND p.Net_pay > 0
          AND UPPER(COALESCE(p.Payment_Status, '')) NOT IN
              ('FAILED', 'REJECTED', 'REVERSED')
        GROUP BY p.Employee_ID
        """,
        [pp, pp],
    ).fetchall()
    return [
        Finding(
            ErrorType.CRITICAL_TERMINATED_PAID, "CRITICAL", emp, pp,
            None, net,
            f"{emp} left on {left} but was paid {net} for {pp}",
        )
        for emp, net, left in rows
    ]


def check_orphan_payroll(conn, pay_period):
    """In payroll, absent from HRIS."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        SELECT p.Employee_ID, SUM(p.Net_pay)
        FROM fact_payroll p
        LEFT JOIN dim_employees e ON e.Employee_ID = p.Employee_ID
        WHERE p.Pay_Period = CAST(? AS DATE) AND e.Employee_ID IS NULL
        GROUP BY p.Employee_ID
        """,
        [pp],
    ).fetchall()
    return [
        Finding(
            ErrorType.ORPHAN_PAYROLL_RECORD, "HIGH", emp, pp,
            None, net, f"{emp} was paid {net} but does not exist in HRIS",
        )
        for emp, net in rows
    ]


def check_duplicate_payment(conn, pay_period):
    """More than one REGULAR payroll row for the same employee + period.
    Manual_Adjustment rows are excluded: a regular payment plus an
    adjustment is an off-cycle item (rule 10), not a double payment."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        SELECT Employee_ID, COUNT(*), SUM(Net_pay)
        FROM fact_payroll
        WHERE Pay_Period = CAST(? AS DATE)
          AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment'
        GROUP BY Employee_ID
        HAVING COUNT(*) > 1
        """,
        [pp],
    ).fetchall()
    return [
        Finding(
            ErrorType.DUPLICATE_PAYMENT, "HIGH", emp, pp,
            None, total,
            f"{emp} has {count} regular payments in {pp} (total {total})",
        )
        for emp, count, total in rows
    ]


def check_base_rate_mismatch(conn, pay_period):
    """HRIS base salary vs the base salary payroll used.
    Manual adjustment rows carry base 0 by design, so they are excluded."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        SELECT p.Employee_ID, e.Base_Salary_HRIS, p.Base_Salary_Payroll
        FROM fact_payroll p
        JOIN dim_employees e ON e.Employee_ID = p.Employee_ID
        WHERE p.Pay_Period = CAST(? AS DATE)
          AND COALESCE(p.Payment_Mode, '') <> 'Manual_Adjustment'
          AND ABS(e.Base_Salary_HRIS - p.Base_Salary_Payroll) > ?
        """,
        [pp, _tolerance()],
    ).fetchall()
    return [
        Finding(
            ErrorType.BASE_RATE_MISMATCH, "MEDIUM", emp, pp,
            hris, payroll, f"HRIS says {hris}, payroll used {payroll}",
        )
        for emp, hris, payroll in rows
    ]


def check_mom_variance(conn, pay_period):
    """Gross pay moved more than the threshold vs the PREVIOUS PAY PERIOD.
    First month (no previous row) and previous = 0 are skipped, never
    flagged. Manual adjustments are excluded so arrears don't trip it."""
    pp = _norm_period(pay_period)
    prev = _prev_period(pp)
    threshold = _cfg("MoM_variance_percentage", 0.15)
    rows = conn.execute(
        """
        WITH cur AS (
            SELECT Employee_ID, SUM(Gross_Pay) AS pay
            FROM fact_payroll
            WHERE Pay_Period = CAST(? AS DATE)
              AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment'
            GROUP BY Employee_ID
        ),
        prv AS (
            SELECT Employee_ID, SUM(Gross_Pay) AS pay
            FROM fact_payroll
            WHERE Pay_Period = CAST(? AS DATE)
              AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment'
            GROUP BY Employee_ID
        )
        SELECT c.Employee_ID, pv.pay, c.pay,
               ROUND((c.pay - pv.pay) / pv.pay * 100, 2)
        FROM cur c
        JOIN prv pv ON pv.Employee_ID = c.Employee_ID
        WHERE pv.pay > 0
          AND ABS(c.pay - pv.pay) / pv.pay > ?
        """,
        [pp, prev, threshold],
    ).fetchall()
    return [
        Finding(
            ErrorType.MOM_VARIANCE, "MEDIUM", emp, pp, prev_pay, cur_pay,
            f"Gross pay changed {pct}% vs {prev} (was {prev_pay}, now {cur_pay})",
        )
        for emp, prev_pay, cur_pay, pct in rows
    ]


def check_headcount_mismatch(conn, pay_period):
    """Do the three systems agree on how many people there are?
    Says THAT counts differ (and which pair), not who. employee_id is None."""
    pp = _norm_period(pay_period)
    hris = conn.execute(
        """
        SELECT COUNT(DISTINCT Employee_ID) FROM dim_employees
        WHERE Date_Of_Joining <= last_day(CAST(? AS DATE))
          AND (Date_Of_Leaving IS NULL OR Date_Of_Leaving >= CAST(? AS DATE))
        """,
        [pp, pp],
    ).fetchone()[0]
    payroll = conn.execute(
        "SELECT COUNT(DISTINCT Employee_ID) FROM fact_payroll "
        "WHERE Pay_Period = CAST(? AS DATE)",
        [pp],
    ).fetchone()[0]
    gl = conn.execute(
        "SELECT COUNT(DISTINCT Employee_ID) FROM fact_gl "
        "WHERE Pay_Period = CAST(? AS DATE)",
        [pp],
    ).fetchone()[0]

    findings = []
    for label, left, right in (
        ("HRIS active vs payroll paid", hris, payroll),
        ("Payroll paid vs GL posted", payroll, gl),
    ):
        if left != right:
            findings.append(
                Finding(
                    ErrorType.HEADCOUNT_MISMATCH, "MEDIUM", None, pp,
                    float(left), float(right),
                    f"{label}: {left} vs {right} headcount in {pp}",
                )
            )
    return findings


def check_off_cycle_adjustment(conn, pay_period):
    """Definition (matches the data): a payroll row is off-cycle if
    Payment_Mode = 'Manual_Adjustment' OR its Payroll_Run_ID is not the
    regular run for this period (RUN_YYYYMM)."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        SELECT Employee_ID, Net_pay, Payment_Mode, Payroll_Run_ID
        FROM fact_payroll
        WHERE Pay_Period = CAST(? AS DATE)
          AND (COALESCE(Payment_Mode, '') = 'Manual_Adjustment'
               OR Payroll_Run_ID <> 'RUN_' || strftime(CAST(? AS DATE), '%Y%m'))
        """,
        [pp, pp],
    ).fetchall()
    return [
        Finding(
            ErrorType.OFF_CYCLE_MANUAL_ADJ, "MEDIUM", emp, pp, None, net,
            f"{emp}: off-cycle payment {net} (mode {mode}, run {run}); "
            f"needs retroactive approval",
        )
        for emp, net, mode, run in rows
    ]


def check_gl_net_mismatch(conn, pay_period):
    """Payroll net vs GL posted, both SUMMED per employee first.
    FULL OUTER so 'paid but not posted' and 'posted but not paid' show up."""
    pp = _norm_period(pay_period)
    rows = conn.execute(
        """
        WITH pt AS (
            SELECT Employee_ID, SUM(Net_pay) AS payroll_total
            FROM fact_payroll
            WHERE Pay_Period = CAST(? AS DATE)
            GROUP BY Employee_ID
        ),
        gt AS (
            SELECT Employee_ID, SUM(GL_Amount_Posted) AS gl_total
            FROM fact_gl
            WHERE Pay_Period = CAST(? AS DATE)
            GROUP BY Employee_ID
        )
        SELECT COALESCE(pt.Employee_ID, gt.Employee_ID),
               pt.payroll_total, gt.gl_total
        FROM pt FULL OUTER JOIN gt ON pt.Employee_ID = gt.Employee_ID
        WHERE ABS(COALESCE(pt.payroll_total, 0) - COALESCE(gt.gl_total, 0)) > ?
        """,
        [pp, pp, _tolerance()],
    ).fetchall()

    out = []
    for emp, paid, posted in rows:
        if posted is None:
            msg = f"{emp}: payroll net {paid} has no GL posting"
        elif paid is None:
            msg = f"{emp}: GL posted {posted} but no payroll record"
        else:
            msg = f"{emp}: payroll net {paid} but GL posted {posted}"
        out.append(
            Finding(ErrorType.GL_NET_MISMATCH, "HIGH", emp, pp, paid, posted, msg)
        )
    return out


def check_esi_boundary(conn, pay_period):
    """Gross within a band just under the ESI wage limit: a RISK flag, not an
    error. Limit and band come from settings (limit 21000, band 3000)."""
    pp = _norm_period(pay_period)
    limit = float(_cfg("ESI_wage_boundary", 21000))
    band = float(_cfg("ESI_band", 3000))
    rows = conn.execute(
        """
        SELECT Employee_ID, Gross_Pay
        FROM fact_payroll
        WHERE Pay_Period = CAST(? AS DATE)
          AND COALESCE(Payment_Mode, '') <> 'Manual_Adjustment'
          AND Gross_Pay BETWEEN ? AND ?
        """,
        [pp, limit - band, limit],
    ).fetchall()
    return [
        Finding(
            ErrorType.ESI_BOUNDARY_RISK, "LOW", emp, pp, limit, gross,
            f"{emp}: gross {gross} is within {band:.0f} of the ESI limit {limit:.0f}",
        )
        for emp, gross in rows
    ]


def check_ot_anomaly(conn, pay_period):
    """Definition: Overtime > OT_limit x Basic_Salary (default 20% of basic).
    A history-based / per-department Z-score version belongs in the insight
    engine."""
    pp = _norm_period(pay_period)
    ot_limit = float(_cfg("OT_limit", 0.20))
    rows = conn.execute(
        """
        SELECT Employee_ID, Basic_Salary, Overtime
        FROM fact_payroll
        WHERE Pay_Period = CAST(? AS DATE)
          AND Basic_Salary > 0
          AND Overtime > Basic_Salary * ?
        """,
        [pp, ot_limit],
    ).fetchall()
    return [
        Finding(
            ErrorType.OT_ANOMALY, "MEDIUM", emp, pp, basic * ot_limit, ot,
            f"{emp}: overtime {ot} exceeds {ot_limit:.0%} of basic ({basic})",
        )
        for emp, basic, ot in rows
    ]


RULES = [
    check_terminated_paid,
    check_orphan_payroll,
    check_duplicate_payment,
    check_base_rate_mismatch,
    check_mom_variance,
    check_headcount_mismatch,
    check_off_cycle_adjustment,
    check_gl_net_mismatch,
    check_esi_boundary,
    check_ot_anomaly,
]


# --------------------------------------------------------------------------
# Persistence + runner
# --------------------------------------------------------------------------
def setup_reconciliation_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_reconciliation (
            error_type  VARCHAR,
            severity    VARCHAR,
            employee_id VARCHAR,
            pay_period  DATE,
            expected    DOUBLE,
            actual      DOUBLE,
            message     VARCHAR,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def run_reconciliation(conn, pay_period):
    """Run every rule for one period, persist findings, return counts.

    * One failing rule never stops the others (logged with traceback).
    * Re-run safe: this period's old findings are deleted and the new ones
      inserted in ONE transaction, so running twice gives identical rows.
    """
    log = _get_logger()
    pp = _norm_period(pay_period)
    log.info("Reconciliation begin for %s", pp)
    setup_reconciliation_table(conn)

    findings: list[Finding] = []
    for rule in RULES:
        try:
            found = rule(conn, pp)
            log.info("%s -> %d finding(s)", rule.__name__, len(found))
            findings.extend(found)
        except Exception:
            log.exception("Rule %s failed", rule.__name__)

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            "DELETE FROM fact_reconciliation WHERE pay_period = CAST(? AS DATE)",
            [pp],
        )
        if findings:
            conn.executemany(
                """
                INSERT INTO fact_reconciliation
                    (error_type, severity, employee_id, pay_period,
                     expected, actual, message)
                VALUES (?, ?, ?, CAST(? AS DATE), ?, ?, ?)
                """,
                [
                    (f.error_type.value, f.severity, f.employee_id, f.pay_period,
                     f.expected, f.actual, f.message)
                    for f in findings
                ],
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        log.exception("Persisting findings failed; rolled back")
        raise

    summary: dict[str, int] = {}
    for f in findings:
        summary[f.error_type.value] = summary.get(f.error_type.value, 0) + 1
    log.info("Reconciliation done for %s: %s", pp, summary)
    return summary


if __name__ == "__main__":
    connection = duckdb.connect(settings.database_path)
    period = sys.argv[1] if len(sys.argv) > 1 else str(
        connection.execute("SELECT MAX(Pay_Period) FROM fact_payroll").fetchone()[0]
    )
    print(run_reconciliation(connection, period))