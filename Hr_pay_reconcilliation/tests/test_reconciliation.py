"""
test_reconciliation.py

Builds a tiny in-memory DuckDB with ONE planted fault per rule, plus a clean
employee (E01) who must never be flagged. Run:  pytest -q
"""
import duckdb
import pytest

from src import reconciliation as rec

PERIOD = "2024-10-01"
PREV = "2024-09-01"
RUN = "RUN_202410"


# --------------------------------------------------------------------------
# Fixture data
# --------------------------------------------------------------------------
def make_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE dim_employees(
            Employee_ID VARCHAR, Employee_Name VARCHAR, Department VARCHAR,
            Date_Of_Joining DATE, Date_Of_Leaving DATE,
            Employment_Status VARCHAR, Base_Salary_HRIS DOUBLE)""")
    conn.execute("""
        CREATE TABLE fact_payroll(
            Employee_ID VARCHAR, Pay_Period DATE, Base_Salary_Payroll DOUBLE,
            Basic_Salary DOUBLE, Overtime DOUBLE, Gross_Pay DOUBLE,
            ESI_deduction DOUBLE, Net_pay DOUBLE, Payment_Mode VARCHAR,
            Payment_Status VARCHAR, Payroll_Run_ID VARCHAR)""")
    conn.execute("""
        CREATE TABLE fact_gl(
            Employee_ID VARCHAR, Pay_Period DATE,
            GL_Account_Code VARCHAR, GL_Amount_Posted DOUBLE)""")

    # (id, joined, left, status, hris_base)
    hris = [
        ("E01", "2020-01-01", None,         "Active",     30000),  # clean control
        ("E02", "2020-01-01", "2024-08-15", "Terminated", 30000),  # left BEFORE period, paid
        ("E03", "2020-01-01", None,         "Active",     30000),  # base rate mismatch
        ("E04", "2020-01-01", "2024-10-15", "Terminated", 30000),  # left MID-period, paid (legit)
        ("E05", "2020-01-01", None,         "Active",     30000),  # duplicate payment
        ("E06", "2020-01-01", None,         "Active",     30000),  # manual adjustment
        ("E07", "2020-01-01", None,         "Active",     30000),  # GL mismatch
        ("E08", "2020-01-01", None,         "Active",     30000),  # ESI boundary
        ("E09", "2020-01-01", None,         "Active",     30000),  # overtime anomaly
        ("E10", "2020-01-01", None,         "Active",     30000),  # MoM jump
        ("E11", "2020-01-01", None,         "Active",     30000),  # active, never paid
    ]
    conn.executemany(
        "INSERT INTO dim_employees VALUES (?, ?, 'OPD', ?, ?, ?, ?)",
        [(i, i, j, l, s, b) for i, j, l, s, b in hris],
    )

    def pay(emp, gross=40000, net=36000, base=30000, basic=15000, ot=0,
            mode="Bank_Transfer", run=RUN, period=PERIOD):
        return (emp, period, base, basic, ot, gross, 0, net, mode,
                "Processed", run)

    payroll = [
        pay("E01"), pay("E01", period=PREV),
        pay("E02"),
        pay("E03", base=33000),
        pay("E04"),
        pay("E05"), pay("E05"),                              # two regular rows
        pay("E06"), pay("E06", gross=5000, net=5000, base=0,
                         mode="Manual_Adjustment", run="ADJ_202410_01"),
        pay("E07", net=25000),
        pay("E08", gross=20000, net=18000),
        pay("E09", basic=20000, ot=6000),                    # 30% of basic
        pay("E10", gross=30000, net=27000),
        pay("E10", gross=20000, net=18000, period=PREV),     # +50% vs prev
        pay("E99"),                                          # not in HRIS
    ]
    conn.executemany(
        "INSERT INTO fact_payroll VALUES (?,?,?,?,?,?,?,?,?,?,?)", payroll
    )

    # GL mirrors payroll for the current period, except E07 (+2000)
    gl = []
    for r in payroll:
        if r[1] != PERIOD:
            continue
        amount = r[7] + (2000 if r[0] == "E07" else 0)
        gl.append((r[0], PERIOD, "6001-Salaries", amount))
    conn.executemany("INSERT INTO fact_gl VALUES (?,?,?,?)", gl)
    return conn


@pytest.fixture(autouse=True)
def fixed_thresholds(monkeypatch):
    monkeypatch.setattr(rec.settings, "MoM_variance_percentage", 0.15, raising=False)
    monkeypatch.setattr(rec.settings, "OT_limit", 0.20, raising=False)
    monkeypatch.setattr(rec.settings, "ESI_wage_boundary", 21000, raising=False)
    monkeypatch.setattr(rec.settings, "ESI_band", 3000, raising=False)
    monkeypatch.setattr(rec.settings, "amount_tolerance", 0.1, raising=False)


@pytest.fixture()
def conn():
    c = make_conn()
    yield c
    c.close()


def ids(findings):
    return {f.employee_id for f in findings}


# --------------------------------------------------------------------------
# One test per rule: finds exactly the planted fault, nothing else
# --------------------------------------------------------------------------
def test_terminated_paid_flags_only_pre_period_leaver(conn):
    found = rec.check_terminated_paid(conn, PERIOD)
    assert ids(found) == {"E02"}          # E04 left mid-month: NOT flagged
    assert found[0].severity == "CRITICAL"


def test_orphan_payroll(conn):
    assert ids(rec.check_orphan_payroll(conn, PERIOD)) == {"E99"}


def test_duplicate_payment_ignores_manual_adjustment(conn):
    # E06 has regular + manual row: that is off-cycle, not a duplicate
    assert ids(rec.check_duplicate_payment(conn, PERIOD)) == {"E05"}


def test_base_rate_mismatch_ignores_manual_adjustment_rows(conn):
    # E06's manual row has base 0 by design and must not be flagged
    assert ids(rec.check_base_rate_mismatch(conn, PERIOD)) == {"E03"}


def test_mom_variance(conn):
    found = rec.check_mom_variance(conn, PERIOD)
    assert ids(found) == {"E10"}
    assert found[0].expected == 20000 and found[0].actual == 30000


def test_mom_first_period_is_skipped_not_flagged(conn):
    # No previous period exists for 2024-09 -> nothing to compare, no findings
    assert rec.check_mom_variance(conn, PREV) == []


def test_headcount_mismatch(conn):
    found = rec.check_headcount_mismatch(conn, PERIOD)
    # HRIS active = 10 (E02 left before period), payroll = 11, GL = 11
    assert len(found) == 1
    assert found[0].employee_id is None
    assert "HRIS" in found[0].message
    assert (found[0].expected, found[0].actual) == (10.0, 11.0)


def test_off_cycle_adjustment(conn):
    assert ids(rec.check_off_cycle_adjustment(conn, PERIOD)) == {"E06"}


def test_gl_net_mismatch(conn):
    found = rec.check_gl_net_mismatch(conn, PERIOD)
    assert ids(found) == {"E07"}
    assert (found[0].expected, found[0].actual) == (25000, 27000)


def test_gl_missing_posting_is_flagged(conn):
    conn.execute("DELETE FROM fact_gl WHERE Employee_ID = 'E01'")
    found = rec.check_gl_net_mismatch(conn, PERIOD)
    assert "E01" in ids(found)


def test_esi_boundary(conn):
    assert ids(rec.check_esi_boundary(conn, PERIOD)) == {"E08"}


def test_ot_anomaly(conn):
    assert ids(rec.check_ot_anomaly(conn, PERIOD)) == {"E09"}


# --------------------------------------------------------------------------
# Whole-engine behaviour
# --------------------------------------------------------------------------
def test_no_false_positives_on_clean_employee(conn):
    for rule in rec.RULES:
        assert "E01" not in ids(rule(conn, PERIOD)), rule.__name__


def test_run_reconciliation_summary_and_persistence(conn):
    summary = rec.run_reconciliation(conn, PERIOD)
    assert summary == {et.value: 1 for et in rec.ErrorType}
    stored = conn.execute(
        "SELECT COUNT(*) FROM fact_reconciliation WHERE pay_period = DATE '2024-10-01'"
    ).fetchone()[0]
    assert stored == 10


def test_run_reconciliation_is_idempotent(conn):
    first = rec.run_reconciliation(conn, PERIOD)
    second = rec.run_reconciliation(conn, PERIOD)
    assert first == second
    assert conn.execute("SELECT COUNT(*) FROM fact_reconciliation").fetchone()[0] == 10


def test_one_failing_rule_does_not_stop_the_others(conn, monkeypatch):
    def boom(conn, pay_period):
        raise RuntimeError("simulated rule failure")

    monkeypatch.setattr(rec, "RULES", [boom, rec.check_orphan_payroll])
    summary = rec.run_reconciliation(conn, PERIOD)
    assert summary == {"ORPHAN_PAYROLL_RECORD": 1}


def test_view_has_one_row_per_employee_and_keeps_orphans(conn):
    df = rec.build_reconciliation_view(conn, PERIOD)
    assert df["Employee_ID"].is_unique
    assert "E99" in set(df["Employee_ID"])       # orphan survives FULL OUTER JOIN
    assert "E11" in set(df["Employee_ID"])       # unpaid employee survives too
    e05 = df[df["Employee_ID"] == "E05"].iloc[0]
    assert e05["payroll_rows"] == 2              # aggregated, not multiplied