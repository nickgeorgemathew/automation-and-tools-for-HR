"""
mock_generator.py
-----------------
Generates three realistic mock CSV feeds for an Indian hospital payroll
reconciliation system:

    1. hris_export.csv       — HR master data (source of truth for headcount)
    2. payroll_register.csv  — Monthly payroll disbursements
    3. gl_dump.csv           — General Ledger finance postings

Intentional errors injected (these are what your reconciliation engine must catch):
    E1 — CRITICAL_TERMINATED_PAID   : Terminated employee still receiving gross pay
    E2 — ORPHAN_PAYROLL_RECORD      : Employee ID in payroll not present in HRIS
    E3 — BASE_RATE_MISMATCH         : HRIS base salary != Payroll base salary
    E4 — OFF_CYCLE_MANUAL_ADJ       : Manual adjustment payment with no HRIS record
    E5 — GL_NET_MISMATCH            : GL posted amount != Payroll net pay

Usage:
    python src/mock_generator.py
    python src/mock_generator.py --employees 100 --month 2024-10
    python src/mock_generator.py --seed 99  # reproducible output
"""

import argparse
import random
import hashlib
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Constants — Indian hospital domain knowledge baked in
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    "Emergency", "ICU", "General_Ward", "OPD", "Surgery",
    "Radiology", "Pathology", "Pharmacy", "Admin", "HR",
    "Housekeeping", "Security", "Accounts", "IT", "Canteen",
]

# Role → (category, base_salary_min, base_salary_max)
ROLES = {
    # Clinical
    "Senior_Consultant":        ("Clinical",     150000, 300000),
    "Junior_Resident_Doctor":   ("Clinical",      60000,  90000),
    "Visiting_Consultant":      ("Clinical",           0,      0),  # Per-procedure, not monthly
    "Head_Nurse":               ("Nursing",        45000,  65000),
    "Staff_Nurse":              ("Nursing",        25000,  40000),
    "ANM":                      ("Nursing",        18000,  28000),
    # Allied Health
    "Radiographer":             ("Allied_Health",  30000,  50000),
    "Lab_Technician":           ("Allied_Health",  22000,  38000),
    "Physiotherapist":          ("Allied_Health",  28000,  45000),
    "Pharmacist":               ("Allied_Health",  25000,  40000),
    # Admin & Support
    "HR_Manager":               ("Admin",          55000,  80000),
    "HR_Executive":             ("Admin",          28000,  45000),
    "Accounts_Officer":         ("Admin",          35000,  55000),
    "IT_Support":               ("Admin",          25000,  40000),
    "Admin_Executive":          ("Admin",          22000,  35000),
    # Support Staff
    "Housekeeping_Staff":       ("Support",        14000,  18000),
    "Security_Guard":           ("Support",        15000,  20000),
    "Canteen_Staff":            ("Support",        13000,  17000),
    "Driver":                   ("Support",        18000,  25000),
}

EMPLOYEE_STATUS = ["Active", "Active", "Active", "Active", "Terminated", "On_Leave"]

INDIAN_FIRST_NAMES = [
    "Anil", "Priya", "Rahul", "Sunita", "Vikram", "Meena", "Rajesh",
    "Kavitha", "Suresh", "Anitha", "Deepak", "Lakshmi", "Mohan", "Rekha",
    "Kiran", "Pooja", "Sanjay", "Divya", "Ramesh", "Nisha", "Ashok",
    "Shilpa", "Vinod", "Usha", "Prakash", "Geeta", "Ganesh", "Swathi",
    "Harish", "Bharathi", "Nikhil", "Revathi", "Sunil", "Manjula",
    "Ravi", "Asha", "Mahesh", "Sarala", "Venkat", "Padma",
]

INDIAN_LAST_NAMES = [
    "Kumar", "Sharma", "Reddy", "Nair", "Pillai", "Iyer", "Rao",
    "Patel", "Singh", "Verma", "Gupta", "Joshi", "Menon", "Das",
    "Krishnan", "Naidu", "Hegde", "Shetty", "Bhat", "Murthy",
]

BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Union_Bank", "Canara", "PNB"]

PAY_PERIOD = "2024-10"  # default, overridden by --month arg


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def generate_employee_id(index: int) -> str:
    """Format: E followed by zero-padded 4-digit number. E0001, E0002, ..."""
    return f"E{index:04d}"


def random_name(rng: random.Random) -> str:
    return f"{rng.choice(INDIAN_FIRST_NAMES)} {rng.choice(INDIAN_LAST_NAMES)}"


def random_doj(rng: random.Random, years_back: int = 10) -> str:
    """Random date of joining within the last N years."""
    today = date.today()
    start = today - timedelta(days=years_back * 365)
    delta = rng.randint(0, (today - start).days - 365)  # at least 1 year tenure
    return (start + timedelta(days=delta)).strftime("%Y-%m-%d")


def random_dol(rng: random.Random, doj_str: str) -> str:
    """Date of leaving — at least 6 months after DOJ."""
    doj = date.fromisoformat(doj_str)
    earliest_dol = doj + timedelta(days=180)
    today = date.today()
    if earliest_dol >= today:
        earliest_dol = today - timedelta(days=30)
    delta = rng.randint(0, (today - earliest_dol).days)
    return (earliest_dol + timedelta(days=delta)).strftime("%Y-%m-%d")


def compute_pf(basic: float) -> float:
    """
    Provident Fund: 12% employee + 12% employer on basic.
    PF wage capped at ₹15,000 for mandatory contribution.
    """
    pf_wage = min(basic, 15000.0)
    return round(pf_wage * 0.12, 2)


def compute_esi(gross: float) -> float:
    """
    ESI: 0.75% employee contribution.
    Applicable only if gross <= ₹21,000/month.
    """
    if gross <= 21000:
        return round(gross * 0.0075, 2)
    return 0.0


def compute_tds(gross: float) -> float:
    """Simplified TDS estimate — old regime slab approximation."""
    annual = gross * 12
    if annual <= 250000:
        return 0.0
    elif annual <= 500000:
        tax = (annual - 250000) * 0.05
    elif annual <= 1000000:
        tax = 12500 + (annual - 500000) * 0.20
    else:
        tax = 112500 + (annual - 1000000) * 0.30
    return round(tax / 12, 2)


def compute_pt(gross: float, state: str = "Karnataka") -> float:
    """
    Professional Tax — Karnataka slabs (most common for Bengaluru hospitals).
    Deducted monthly but capped at ₹2,400/year (₹200/month above ₹15,000).
    """
    if gross > 15000:
        return 200.0
    elif gross > 10000:
        return 150.0
    elif gross > 7500:
        return 100.0
    return 0.0


def build_salary_components(rng: random.Random, base_salary: float) -> dict:
    """
    Break base salary into standard Indian payroll components.
    Returns dict of all pay components.
    """
    # Standard split: Basic = 40-50% of CTC
    basic = round(base_salary * rng.uniform(0.40, 0.50), 2)
    hra = round(basic * rng.uniform(0.40, 0.50), 2)           # HRA: 40-50% of basic
    da = round(basic * rng.uniform(0.05, 0.15), 2)            # DA: 5-15% of basic
    ta = round(rng.uniform(1000, 3000), 2)                    # Fixed transport allowance
    medical_allowance = round(rng.uniform(500, 1500), 2)
    special_allowance = round(base_salary - basic - hra - da - ta - medical_allowance, 2)
    special_allowance = max(special_allowance, 0)

    gross = round(basic + hra + da + ta + medical_allowance + special_allowance, 2)

    # Overtime: nurses, housekeeping, security have variable OT
    overtime = 0.0
    if rng.random() < 0.25:  # 25% of employees have OT this month
        overtime = round(rng.uniform(500, 5000), 2)

    gross_with_ot = round(gross + overtime, 2)

    # Deductions
    pf = compute_pf(basic)
    esi = compute_esi(gross_with_ot)
    tds = compute_tds(gross_with_ot)
    pt = compute_pt(gross_with_ot)
    loan_deduction = round(rng.uniform(0, 2000), 2) if rng.random() < 0.15 else 0.0

    total_deductions = round(pf + esi + tds + pt + loan_deduction, 2)
    net_pay = round(gross_with_ot - total_deductions, 2)

    return {
        "Basic_Salary": basic,
        "HRA": hra,
        "DA": da,
        "Transport_Allowance": ta,
        "Medical_Allowance": medical_allowance,
        "Special_Allowance": special_allowance,
        "Overtime": overtime,
        "Gross_Pay": gross_with_ot,
        "PF_Deduction": pf,
        "ESI_Deduction": esi,
        "TDS_Deduction": tds,
        "PT_Deduction": pt,
        "Loan_Deduction": loan_deduction,
        "Total_Deductions": total_deductions,
        "Net_Pay": net_pay,
    }


# ---------------------------------------------------------------------------
# Generator 1: HRIS Export
# ---------------------------------------------------------------------------

def generate_hris(n_employees: int, rng: random.Random) -> pd.DataFrame:
    """
    Simulates an HR Information System export.
    This is the source of truth — who is (or was) employed.
    """
    records = []
    roles = list(ROLES.keys())

    for i in range(1, n_employees + 1):
        emp_id = generate_employee_id(i)
        role = rng.choice(roles)
        category, sal_min, sal_max = ROLES[role]

        # Visiting consultants are paid per procedure — skip from monthly HRIS salary
        if role == "Visiting_Consultant":
            base_salary = 0.0
        else:
            base_salary = round(rng.uniform(sal_min, sal_max), 2)

        status = rng.choice(EMPLOYEE_STATUS)
        doj = random_doj(rng)
        dol = random_dol(rng, doj) if status == "Terminated" else ""

        dept = rng.choice(DEPARTMENTS)
        bank = rng.choice(BANKS)
        account_suffix = rng.randint(1000, 9999)

        records.append({
            "Employee_ID": emp_id,
            "Employee_Name": random_name(rng),
            "Department": dept,
            "Designation": role,
            "Category": category,
            "Date_Of_Joining": doj,
            "Date_Of_Leaving": dol,
            "Employment_Status": status,
            "Base_Salary_HRIS": base_salary,
            "Bank_Name": bank,
            "Bank_Account": f"XXXX{account_suffix}",
            "UAN_Number": f"UAN{rng.randint(100000000, 999999999)}",
            "PAN_Number": f"XXXXX{rng.randint(1000, 9999)}X",
            "Location": rng.choice(["Main_Campus", "Branch_Koramangala", "Branch_Whitefield"]),
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Generator 2: Payroll Register
# ---------------------------------------------------------------------------

def generate_payroll(hris_df: pd.DataFrame, pay_period: str,
                     rng: random.Random) -> pd.DataFrame:
    """
    Simulates a monthly payroll run.
    Starts from HRIS active employees, then injects errors.
    """
    # Only Active employees get paid in a clean run
    active = hris_df[hris_df["Employment_Status"] == "Active"].copy()

    records = []
    for _, row in active.iterrows():
        if row["Base_Salary_HRIS"] == 0:
            continue  # Visiting consultants handled separately
        components = build_salary_components(rng, row["Base_Salary_HRIS"])
        records.append({
            "Employee_ID": row["Employee_ID"],
            "Employee_Name": row["Employee_Name"],
            "Department": row["Department"],
            "Pay_Period": pay_period,
            "Base_Salary_Payroll": row["Base_Salary_HRIS"],  # will be tampered for E3
            **components,
            "Payment_Mode": "Bank_Transfer",
            "Payment_Status": "Processed",
            "Payroll_Run_ID": f"RUN_{pay_period.replace('-', '')}",
            "Remarks": "",
        })

    df = pd.DataFrame(records)

    # -------------------------------------------------------------------
    # Inject intentional errors
    # -------------------------------------------------------------------

    # E1 — CRITICAL_TERMINATED_PAID
    # Pick 2 terminated employees and add them to payroll anyway
    terminated = hris_df[hris_df["Employment_Status"] == "Terminated"].sample(
        n=min(2, len(hris_df[hris_df["Employment_Status"] == "Terminated"])),
        random_state=rng.randint(0, 9999)
    )
    e1_records = []
    for _, row in terminated.iterrows():
        if row["Base_Salary_HRIS"] == 0:
            continue
        components = build_salary_components(rng, row["Base_Salary_HRIS"])
        e1_records.append({
            "Employee_ID": row["Employee_ID"],
            "Employee_Name": row["Employee_Name"],
            "Department": row["Department"],
            "Pay_Period": pay_period,
            "Base_Salary_Payroll": row["Base_Salary_HRIS"],
            **components,
            "Payment_Mode": "Bank_Transfer",
            "Payment_Status": "Processed",
            "Payroll_Run_ID": f"RUN_{pay_period.replace('-', '')}",
            "Remarks": "",  # intentionally blank — no flag raised by payroll team
        })
    if e1_records:
        df = pd.concat([df, pd.DataFrame(e1_records)], ignore_index=True)

    # E2 — ORPHAN_PAYROLL_RECORD
    # Add a payment for an Employee_ID that doesn't exist in HRIS at all
    ghost_ids = ["E9901", "E9902"]
    for ghost_id in ghost_ids:
        ghost_salary = round(rng.uniform(25000, 60000), 2)
        components = build_salary_components(rng, ghost_salary)
        df = pd.concat([df, pd.DataFrame([{
            "Employee_ID": ghost_id,
            "Employee_Name": f"Ghost Employee {ghost_id}",
            "Department": rng.choice(DEPARTMENTS),
            "Pay_Period": pay_period,
            "Base_Salary_Payroll": ghost_salary,
            **components,
            "Payment_Mode": "Bank_Transfer",
            "Payment_Status": "Processed",
            "Payroll_Run_ID": f"RUN_{pay_period.replace('-', '')}",
            "Remarks": "",
        }])], ignore_index=True)

    # E3 — BASE_RATE_MISMATCH
    # Tamper base salary for 3 random active employees (raise by 8-15%)
    mismatch_indices = df.sample(n=min(3, len(df)), random_state=42).index
    for idx in mismatch_indices:
        original = df.loc[idx, "Base_Salary_Payroll"]
        tampered = round(original * rng.uniform(1.08, 1.15), 2)
        df.loc[idx, "Base_Salary_Payroll"] = tampered
        df.loc[idx, "Gross_Pay"] = round(df.loc[idx, "Gross_Pay"] + (tampered - original), 2)
        df.loc[idx, "Net_Pay"] = round(df.loc[idx, "Net_Pay"] + (tampered - original), 2)

    # E4 — OFF_CYCLE_MANUAL_ADJUSTMENT
    # Add 2 manual adjustment entries (bonus/correction) not in HRIS
    for k in range(1, 3):
        # Pick a real active employee and give them an "adjustment"
        if len(df) > 0:
            sample_row = df[df["Employee_ID"].str.startswith("E0")].sample(1).iloc[0]
            adj_amount = round(rng.uniform(3000, 15000), 2)
            df = pd.concat([df, pd.DataFrame([{
                "Employee_ID": sample_row["Employee_ID"],
                "Employee_Name": sample_row["Employee_Name"],
                "Department": sample_row["Department"],
                "Pay_Period": pay_period,
                "Base_Salary_Payroll": 0.0,
                "Basic_Salary": 0.0,
                "HRA": 0.0,
                "DA": 0.0,
                "Transport_Allowance": 0.0,
                "Medical_Allowance": 0.0,
                "Special_Allowance": adj_amount,
                "Overtime": 0.0,
                "Gross_Pay": adj_amount,
                "PF_Deduction": 0.0,
                "ESI_Deduction": 0.0,
                "TDS_Deduction": 0.0,
                "PT_Deduction": 0.0,
                "Loan_Deduction": 0.0,
                "Total_Deductions": 0.0,
                "Net_Pay": adj_amount,
                "Payment_Mode": "Manual_Adjustment",
                "Payment_Status": "Processed",
                "Payroll_Run_ID": f"ADJ_{pay_period.replace('-', '')}_{k:02d}",
                "Remarks": "Manual off-cycle adjustment",
            }])], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# Generator 3: GL Dump
# ---------------------------------------------------------------------------

def generate_gl(payroll_df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """
    Simulates a General Ledger export from the finance system.
    Mostly mirrors payroll net pay, but with E5 mismatches injected.
    """
    records = []

    for _, row in payroll_df.iterrows():
        # E5 — GL_NET_MISMATCH: tamper GL amount for ~5% of records
        if rng.random() < 0.05:
            gl_amount = round(row["Net_Pay"] * rng.uniform(0.92, 1.08), 2)
            gl_remark = "Posting_Discrepancy"
        else:
            gl_amount = row["Net_Pay"]
            gl_remark = "Auto_Posted"

        records.append({
            "GL_Entry_ID": f"GL{rng.randint(100000, 999999)}",
            "Employee_ID": row["Employee_ID"],
            "Department": row["Department"],
            "Pay_Period": row["Pay_Period"],
            "GL_Account_Code": rng.choice(["6001-Salaries", "6002-Wages", "6003-Allowances"]),
            "GL_Amount_Posted": gl_amount,
            "Payroll_Net_Pay_Reference": row["Net_Pay"],
            "Posting_Date": f"{row['Pay_Period']}-28",
            "Posted_By": rng.choice(["finance_auto_sync", "accounts_officer_01", "accounts_officer_02"]),
            "GL_Remarks": gl_remark,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate mock hospital payroll CSVs")
    parser.add_argument("--employees", type=int, default=80,
                        help="Number of employees to generate (default: 80)")
    parser.add_argument("--month", type=str, default="2024-10",
                        help="Pay period in YYYY-MM format (default: 2024-10)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output-dir", type=str, default="data/incoming_feeds",
                        help="Output directory for CSVs")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating mock data: {args.employees} employees, period {args.month}, seed {args.seed}")
    print("-" * 60)

    # Generate HRIS
    print("  [1/3] Generating HRIS export...")
    hris_df = generate_hris(args.employees, rng)
    hris_path = output_dir / "hris_export.csv"
    hris_df.to_csv(hris_path, index=False)
    print(f"        Saved → {hris_path}  ({len(hris_df)} records)")

    # Generate Payroll Register
    print("  [2/3] Generating Payroll Register...")
    payroll_df = generate_payroll(hris_df, args.month, rng)
    payroll_path = output_dir / "payroll_register.csv"
    payroll_df.to_csv(payroll_path, index=False)
    print(f"        Saved → {payroll_path}  ({len(payroll_df)} records)")

    # Generate GL Dump
    print("  [3/3] Generating GL Dump...")
    gl_df = generate_gl(payroll_df, rng)
    gl_path = output_dir / "gl_dump.csv"
    gl_df.to_csv(gl_path, index=False)
    print(f"        Saved → {gl_path}  ({len(gl_df)} records)")

    # Summary of injected errors
    print()
    print("Injected errors summary:")
    print("-" * 60)

    terminated_paid = hris_df[hris_df["Employment_Status"] == "Terminated"]["Employee_ID"].tolist()
    e1_caught = payroll_df[payroll_df["Employee_ID"].isin(terminated_paid)]
    print(f"  E1 CRITICAL_TERMINATED_PAID  : {len(e1_caught)} record(s)")
    print(f"     IDs: {e1_caught['Employee_ID'].tolist()}")

    hris_ids = set(hris_df["Employee_ID"])
    e2_caught = payroll_df[~payroll_df["Employee_ID"].isin(hris_ids) &
                            ~payroll_df["Employee_ID"].str.startswith("E990")]
    orphans = payroll_df[payroll_df["Employee_ID"].str.startswith("E990")]
    print(f"  E2 ORPHAN_PAYROLL_RECORD     : {len(orphans)} record(s)")
    print(f"     IDs: {orphans['Employee_ID'].tolist()}")

    print(f"  E3 BASE_RATE_MISMATCH        : ~3 records (salary tampered 8-15%)")
    manual_adj = payroll_df[payroll_df["Payment_Mode"] == "Manual_Adjustment"]
    print(f"  E4 OFF_CYCLE_MANUAL_ADJ      : {len(manual_adj)} record(s)")
    gl_mismatch = gl_df[gl_df["GL_Amount_Posted"] != gl_df["Payroll_Net_Pay_Reference"]]
    print(f"  E5 GL_NET_MISMATCH           : {len(gl_mismatch)} record(s)")
    print()
    print("Run your reconciliation engine on these files to catch all 5 error types.")
    print(f"Output directory: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
