"""
mock_generator.py  (v2)
-----------------------
Generates three mock hospital feeds for N consecutive months, keyed by Pay_Period:

    hris_export.csv       HR master snapshot (one row per employee)
    payroll_register.csv  Payroll rows for every month
    gl_dump.csv           Finance postings for every month
    injected_faults.json  GROUND TRUTH: exactly what the engine must find

Earlier months are CLEAN. Faults are injected into the LAST month only, so the
reconciliation tests can assert "finds exactly the faults you injected".

Injected faults (last month), one employee each unless stated:
    E1  CRITICAL_TERMINATED_PAID  2 employees who left BEFORE the first period, still paid
    E2  ORPHAN_PAYROLL_RECORD     2 ghost IDs (E9901, E9902) paid but absent from HRIS
    E3  BASE_RATE_MISMATCH        3 employees, payroll base 8-12% above HRIS
    E4  OFF_CYCLE_MANUAL_ADJ      2 manual adjustment rows (Payment_Mode = Manual_Adjustment)
    E5  GL_NET_MISMATCH           2 employees where finance posted a different amount
    E6  DUPLICATE_PAYMENT         1 employee paid twice in the same run
    E7  MOM_VARIANCE (40% jump)   1 employee, special allowance +40% of base
    E8  OT_ANOMALY                1 employee, overtime = 60% of basic
Also a legitimate mid-month leaver (must NOT be flagged) and natural
ESI-band employees (low-pay roles) that raise ESI_BOUNDARY_RISK.

Usage:
    python src/mock_generator.py
    python src/mock_generator.py --employees 100 --month 2024-10 --months 3 --seed 99
"""

import argparse
import copy
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    "Emergency", "ICU", "General_Ward", "OPD", "Surgery",
    "Radiology", "Pathology", "Pharmacy", "Admin", "HR",
    "Housekeeping", "Security", "Accounts", "IT", "Canteen",
]

# Role -> (category, base_salary_min, base_salary_max)
# Visiting_Consultant is intentionally absent: they are paid per procedure,
# outside monthly payroll, and v2 only allows a zero HRIS salary for leavers.
ROLES = {
    "Senior_Consultant":      ("Clinical",      150000, 300000),
    "Junior_Resident_Doctor": ("Clinical",       60000,  90000),
    "Head_Nurse":             ("Nursing",        45000,  65000),
    "Staff_Nurse":            ("Nursing",        25000,  40000),
    "ANM":                    ("Nursing",        18000,  28000),
    "Radiographer":           ("Allied_Health",  30000,  50000),
    "Lab_Technician":         ("Allied_Health",  22000,  38000),
    "Physiotherapist":        ("Allied_Health",  28000,  45000),
    "Pharmacist":             ("Allied_Health",  25000,  40000),
    "HR_Manager":             ("Admin",          55000,  80000),
    "HR_Executive":           ("Admin",          28000,  45000),
    "Accounts_Officer":       ("Admin",          35000,  55000),
    "IT_Support":             ("Admin",          25000,  40000),
    "Admin_Executive":        ("Admin",          22000,  35000),
    "Housekeeping_Staff":     ("Support",        14000,  18000),
    "Security_Guard":         ("Support",        15000,  20000),
    "Canteen_Staff":          ("Support",        13000,  17000),
    "Driver":                 ("Support",        18000,  25000),
}

EMPLOYEE_STATUS = ["Active", "Active", "Active", "Active", "Terminated", "On_Leave"]
FIRST_NAMES = [
    "Anil", "Priya", "Rahul", "Sunita", "Vikram", "Meena", "Rajesh", "Kavitha", "Suresh",
    "Anitha", "Deepak", "Lakshmi", "Mohan", "Rekha", "Kiran", "Pooja", "Sanjay", "Divya",
    "Ramesh", "Nisha", "Ashok", "Shilpa", "Vinod", "Usha", "Prakash", "Geeta", "Ganesh",
    "Swathi", "Harish", "Bharathi", "Nikhil", "Revathi", "Sunil", "Manjula", "Ravi", "Asha",
    "Mahesh", "Sarala", "Venkat", "Padma",
]
LAST_NAMES = [
    "Kumar", "Sharma", "Reddy", "Nair", "Pillai", "Iyer", "Rao", "Patel", "Singh", "Verma",
    "Gupta", "Joshi", "Menon", "Das", "Krishnan", "Naidu", "Hegde", "Shetty", "Bhat", "Murthy",
]
BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Union_Bank", "Canara", "PNB"]
LOCATIONS = ["Main_Campus", "Branch_Koramangala", "Branch_Whitefield"]
GL_ACCOUNTS = ["6001-Salaries", "6002-Wages", "6003-Allowances"]
GL_USERS = ["finance_auto_sync", "accounts_officer_01", "accounts_officer_02"]


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def month_start(ym: str) -> date:
    return date.fromisoformat(ym + "-01")


def add_months(d: date, n: int) -> date:
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)


def month_end(d: date) -> date:
    return add_months(d, 1) - timedelta(days=1)


def rand_date(rng: random.Random, lo: date, hi: date) -> date:
    return lo + timedelta(days=rng.randint(0, max((hi - lo).days, 0)))


# ---------------------------------------------------------------------------
# Statutory formulas (used for realistic deductions)
# ---------------------------------------------------------------------------
def compute_pf(basic: float) -> float:
    """PF: 12% employee share on basic, wage capped at 15,000."""
    return round(min(basic, 15000.0) * 0.12, 2)


def compute_esi(gross: float) -> float:
    """ESI: 0.75% employee share, applicable only up to 21,000 gross."""
    return round(gross * 0.0075, 2) if gross <= 21000 else 0.0


def compute_tds(gross: float) -> float:
    """Simplified old-regime TDS estimate."""
    annual = gross * 12
    if annual <= 250000:
        return 0.0
    if annual <= 500000:
        tax = (annual - 250000) * 0.05
    elif annual <= 1000000:
        tax = 12500 + (annual - 500000) * 0.20
    else:
        tax = 112500 + (annual - 1000000) * 0.30
    return round(tax / 12, 2)


def compute_pt(gross: float) -> float:
    """Karnataka professional tax slabs."""
    if gross > 15000:
        return 200.0
    if gross > 10000:
        return 150.0
    if gross > 7500:
        return 100.0
    return 0.0


# ---------------------------------------------------------------------------
# Salary structure: fixed per employee, so clean months only drift through OT
# ---------------------------------------------------------------------------
def salary_structure(rng: random.Random, base: float) -> dict:
    return {
        "basic_pct": rng.uniform(0.40, 0.50),
        "hra_pct": rng.uniform(0.40, 0.50),   # of basic
        "da_pct": rng.uniform(0.05, 0.15),    # of basic
        "ta": round(min(rng.uniform(1000, 3000), 0.05 * base), 2),
        "med": round(min(rng.uniform(500, 1500), 0.03 * base), 2),
        "loan": round(rng.uniform(0, 2000), 2) if rng.random() < 0.15 else 0.0,
    }


def components(st: dict, base: float, ot: float = 0.0, extra: float = 0.0) -> dict:
    """Break base salary into pay components; gross = base + ot + extra."""
    basic = round(base * st["basic_pct"], 2)
    hra = round(basic * st["hra_pct"], 2)
    da = round(basic * st["da_pct"], 2)
    special = round(base - basic - hra - da - st["ta"] - st["med"] + extra, 2)
    gross = round(basic + hra + da + st["ta"] + st["med"] + special + ot, 2)
    pf, esi, tds, pt = compute_pf(basic), compute_esi(gross), compute_tds(gross), compute_pt(gross)
    total = round(pf + esi + tds + pt + st["loan"], 2)
    return {
        "Basic_Salary": basic, "HRA": hra, "DA": da,
        "Transport_Allowance": st["ta"], "Medical_Allowance": st["med"],
        "Special_Allowance": special, "Overtime": round(ot, 2), "Gross_Pay": gross,
        "PF_Deduction": pf, "ESI_Deduction": esi, "TDS_Deduction": tds,
        "PT_Deduction": pt, "Loan_Deduction": st["loan"],
        "Total_Deductions": total, "Net_Pay": round(gross - total, 2),
    }


# ---------------------------------------------------------------------------
# HRIS
# ---------------------------------------------------------------------------
def generate_hris(n: int, rng: random.Random, first_period: date) -> pd.DataFrame:
    """Dates are anchored to the FIRST pay period so the data is self-consistent:
    leavers left before the first period; everyone else joined at least a year before it."""
    rows = []
    roles = list(ROLES)
    for i in range(1, n + 1):
        role = rng.choice(roles)
        category, lo, hi = ROLES[role]
        status = rng.choice(EMPLOYEE_STATUS)
        if status == "Terminated":
            doj = rand_date(rng, first_period - timedelta(days=3650), first_period - timedelta(days=800))
            dol = rand_date(rng, first_period - timedelta(days=540), first_period - timedelta(days=1))
        else:
            doj = rand_date(rng, first_period - timedelta(days=3650), first_period - timedelta(days=365))
            dol = None
        rows.append({
            "Employee_ID": f"E{i:04d}",
            "Employee_Name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "Department": rng.choice(DEPARTMENTS),
            "Designation": role,
            "Category": category,
            "Date_Of_Joining": doj.isoformat(),
            "Date_Of_Leaving": dol.isoformat() if dol else "",
            "Employment_Status": status,
            "Base_Salary_HRIS": round(rng.uniform(lo, hi), 2),
            "Bank_Name": rng.choice(BANKS),
            "Bank_Account": f"XXXX{rng.randint(1000, 9999)}",   # masked on purpose
            "UAN_Number": f"UAN{rng.randint(100000000, 999999999)}",
            "PAN_Number": f"XXXXX{rng.randint(1000, 9999)}X",
            "Location": rng.choice(LOCATIONS),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Payroll + GL
# ---------------------------------------------------------------------------
def _row(emp: dict, period: date, base: float, comp: dict, mode="Bank_Transfer",
         run=None, remarks="") -> dict:
    return {
        "Employee_ID": emp["Employee_ID"], "Employee_Name": emp["Employee_Name"],
        "Department": emp["Department"], "Pay_Period": period.isoformat(),
        "Base_Salary_Payroll": base, **comp,
        "Payment_Mode": mode, "Payment_Status": "Processed",
        "Payroll_Run_ID": run or f"RUN_{period:%Y%m}", "Remarks": remarks,
    }


def generate_payroll(hris: pd.DataFrame, periods: list[date], rng: random.Random):
    """Returns (payroll_df, faults) where faults is the injected ground truth."""
    emps = {r["Employee_ID"]: r for r in hris.to_dict("records")}
    last, first = periods[-1], periods[0]

    # A legitimate mid-month leaver in the last period: paid correctly, must NOT be flagged.
    active_ids = [e for e, r in emps.items() if r["Employment_Status"] == "Active"]
    mid_leaver = rng.choice(active_ids)
    emps[mid_leaver]["Employment_Status"] = "Terminated"
    emps[mid_leaver]["Date_Of_Leaving"] = (last + timedelta(days=14)).isoformat()
    hris.loc[hris["Employee_ID"] == mid_leaver, ["Employment_Status", "Date_Of_Leaving"]] = \
        ["Terminated", emps[mid_leaver]["Date_Of_Leaving"]]

    def payable(emp, period):
        doj = date.fromisoformat(emp["Date_Of_Joining"])
        dol = date.fromisoformat(emp["Date_Of_Leaving"]) if emp["Date_Of_Leaving"] else None
        return doj <= month_end(period) and (dol is None or dol >= period) and emp["Base_Salary_HRIS"] > 0

    structures = {e: salary_structure(rng, r["Base_Salary_HRIS"]) for e, r in emps.items()}
    ot_by = {}
    rows = {p: [] for p in periods}
    for p in periods:
        for eid, emp in emps.items():
            if not payable(emp, p):
                continue
            base = emp["Base_Salary_HRIS"]
            ot = min(round(rng.uniform(300, 1200), 2), 0.08 * base) if rng.random() < 0.25 else 0.0
            ot_by[(eid, p)] = ot
            rows[p].append(_row(emp, p, base, components(structures[eid], base, ot)))

    # ------------------- inject faults into the LAST period -------------------
    prev = periods[-2] if len(periods) > 1 else None
    quiet = [r["Employee_ID"] for r in rows[last]
             if r["Employee_ID"] != mid_leaver
             and ot_by[(r["Employee_ID"], last)] == 0
             and (prev is None or ot_by.get((r["Employee_ID"], prev), 0) == 0)
             and (prev is None or any(x["Employee_ID"] == r["Employee_ID"] for x in rows[prev]))]
    rng.shuffle(quiet)
    take = lambda k: [quiet.pop() for _ in range(k)]   # noqa: E731  distinct employees per fault
    e3_ids, e7_ids, e8_ids, e6_ids, e5_ids, e4_ids = take(3), take(1), take(1), take(1), take(2), take(2)
    by_id = {r["Employee_ID"]: r for r in rows[last]}

    # E3 base rate mismatch: payroll base 8-12% above HRIS, components rebuilt on the new base
    for eid in e3_ids:
        new_base = round(emps[eid]["Base_Salary_HRIS"] * rng.uniform(1.08, 1.12), 2)
        by_id[eid].update({"Base_Salary_Payroll": new_base, **components(structures[eid], new_base)})
    # E7 40% jump: special allowance + 40% of base (base itself untouched -> not a rate mismatch)
    for eid in e7_ids:
        b = emps[eid]["Base_Salary_HRIS"]
        by_id[eid].update(components(structures[eid], b, extra=round(0.40 * b, 2)))
    # E8 overtime anomaly: overtime = 60% of basic
    for eid in e8_ids:
        b = emps[eid]["Base_Salary_HRIS"]
        ot = round(0.60 * round(b * structures[eid]["basic_pct"], 2), 2)
        by_id[eid].update(components(structures[eid], b, ot=ot))
    # E6 duplicate: identical regular row posted twice in the same run
    for eid in e6_ids:
        rows[last].append(copy.deepcopy(by_id[eid]))
    # E4 manual adjustments
    for k, eid in enumerate(e4_ids, 1):
        amt = round(rng.uniform(3000, 15000), 2)
        comp = {c: 0.0 for c in components(structures[eid], 1)}
        comp.update({"Special_Allowance": amt, "Gross_Pay": amt, "Net_Pay": amt})
        rows[last].append(_row(emps[eid], last, 0.0, comp, "Manual_Adjustment",
                               f"ADJ_{last:%Y%m}_{k:02d}", "Manual off-cycle adjustment"))
    # E1 terminated employees (left before the first period) still paid
    leavers = [e for e, r in emps.items()
               if r["Employment_Status"] == "Terminated" and e != mid_leaver and r["Base_Salary_HRIS"] > 0]
    e1_ids = sorted(rng.sample(leavers, min(2, len(leavers))))
    for eid in e1_ids:
        b = emps[eid]["Base_Salary_HRIS"]
        rows[last].append(_row(emps[eid], last, b, components(structures[eid], b)))
    # E2 orphans (ghost employees)
    ghosts = ["E9901", "E9902"]
    for gid in ghosts:
        b = round(rng.uniform(25000, 60000), 2)
        ghost = {"Employee_ID": gid, "Employee_Name": f"Ghost Employee {gid}",
                 "Department": rng.choice(DEPARTMENTS)}
        rows[last].append(_row(ghost, last, b, components(salary_structure(rng, b), b)))

    payroll = pd.DataFrame([r for p in periods for r in rows[p]])
    faults = {"E1": e1_ids, "E2": ghosts, "E3": e3_ids, "E4": e4_ids, "E5": e5_ids,
              "E6": e6_ids, "E7": e7_ids, "E8": e8_ids, "mid_month_leaver": mid_leaver}
    return payroll, faults


def generate_gl(payroll: pd.DataFrame, rng: random.Random, last: date, e5_ids: list[str]) -> pd.DataFrame:
    """GL mirrors payroll net pay row for row; only E5 employees are posted wrongly."""
    out = []
    for n, row in enumerate(payroll.to_dict("records"), 1):
        wrong = row["Pay_Period"] == last.isoformat() and row["Employee_ID"] in e5_ids \
            and row["Payment_Mode"] == "Bank_Transfer"
        amount = round(row["Net_Pay"] * rng.uniform(1.03, 1.08), 2) if wrong else row["Net_Pay"]
        out.append({
            "GL_Entry_ID": f"GL{n:06d}", "Employee_ID": row["Employee_ID"],
            "Department": row["Department"], "Pay_Period": row["Pay_Period"],
            "GL_Account_Code": rng.choice(GL_ACCOUNTS), "GL_Amount_Posted": amount,
            "Payroll_Net_Pay_Reference": row["Net_Pay"],
            "Posting_Date": row["Pay_Period"][:8] + "28", "Posted_By": rng.choice(GL_USERS),
            "GL_Remarks": "Posting_Discrepancy" if wrong else "Auto_Posted",
        })
    return pd.DataFrame(out)


def expected_findings(faults: dict) -> dict:
    """What the reconciliation engine must report for the last period (ground truth)."""
    return {
        "CRITICAL_TERMINATED_PAID": sorted(faults["E1"]),
        "ORPHAN_PAYROLL_RECORD": sorted(faults["E2"]),
        "BASE_RATE_MISMATCH": sorted(faults["E3"]),
        "OFF_CYCLE_MANUAL_ADJ": sorted(faults["E4"]),
        "GL_NET_MISMATCH": sorted(faults["E5"]),
        "DUPLICATE_PAYMENT": sorted(faults["E6"]),
        # a doubled payment, a 40% jump and a 60%-of-basic overtime all move gross by >15%
        "MOM_VARIANCE": sorted(set(faults["E6"] + faults["E7"] + faults["E8"])),
        "OT_ANOMALY": sorted(faults["E8"]),
        "HEADCOUNT_MISMATCH": 1,   # HRIS active vs payroll paid differs (leavers + ghosts paid)
        "_note": "ESI_BOUNDARY_RISK is natural (low-pay roles) and is not part of the exact check",
    }


def generate_all(employees: int, last_month: str, months: int, seed: int, output_dir) -> dict:
    rng = random.Random(seed)
    last = month_start(last_month)
    periods = [add_months(last, -(months - 1 - i)) for i in range(months)]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    hris = generate_hris(employees, rng, periods[0])
    payroll, faults = generate_payroll(hris, periods, rng)
    gl = generate_gl(payroll, rng, last, faults["E5"])

    hris.to_csv(out / "hris_export.csv", index=False)
    payroll.to_csv(out / "payroll_register.csv", index=False)
    gl.to_csv(out / "gl_dump.csv", index=False)
    manifest = {"seed": seed, "periods": [p.isoformat() for p in periods],
                "fault_period": last.isoformat(), "faults": faults,
                "expected": expected_findings(faults),
                "rows": {"hris": len(hris), "payroll": len(payroll), "gl": len(gl)}}
    (out / "injected_faults.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Generate mock hospital payroll CSVs")
    ap.add_argument("--employees", type=int, default=80)
    ap.add_argument("--month", default="2024-10", help="LAST pay period, YYYY-MM")
    ap.add_argument("--months", type=int, default=3, help="consecutive months to generate")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-dir", default="src/data/incoming_feeds")
    a = ap.parse_args()

    m = generate_all(a.employees, a.month, a.months, a.seed, a.output_dir)
    print(f"Periods: {m['periods']}  seed={a.seed}  rows={m['rows']}")
    print(f"Faults injected into {m['fault_period']}:")
    for k, v in m["expected"].items():
        if not k.startswith("_"):
            print(f"  {k:26s} {v}")
    print(f"Ground truth written to {Path(a.output_dir) / 'injected_faults.json'}")


if __name__ == "__main__":
    main()