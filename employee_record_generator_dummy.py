#!/usr/bin/env python3
"""Generate a dummy employee roll that follows the category template.

The category values (Department, Division, Location, Grade, ...) are read from the
template workbook exactly as typed - including trailing spaces and typos - so the
output behaves like the real sheet will. Only the *relationships* between columns
(which Division sits under which Department, etc.) are assumptions, defined in LEAVES.

Usage:
    python generate_dummy_employee_records.py \
        --template employee records.xlsx --out employee_records_dummy.xlsx \
        --rows 500 --seed 42 [--today 2026-09-19]
"""
import argparse
import random
import re
from collections import defaultdict
from datetime import date, timedelta

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

CATEGORY_COLUMNS = [
    "Department Group", "Department", "Division", "Sub Division", "Location",
    "Designation", "Grade", "Group Stage", "Category", "Ccenter", "Punit",
    "Wunit", "Left", "Status",
]

# --------------------------------------------------------------------------- #
# Assumed org structure. Names are matched to the template ignoring case and
# whitespace, then written using the template's exact spelling.
# --------------------------------------------------------------------------- #
GROUP_OF_DEPT = {
    "Cardiology": "Clinical", "Clinical Nursing": "Clinical",
    "Clinical Nutrition & Dietetics": "Clinical", "Curtis": "Clinical",
    "Biomedical": "Clinical Support", "Clinical Support": "Clinical Support",
    "Lab": "Clinical Support", "Pharmacy": "Clinical Support",
    "Administrative Office": "Non-Clinical", "Branding": "Non-Clinical",
    "Business Development": "Non-Clinical", "Facility Services": "Non-Clinical",
    "Finance and Accounts": "Non-Clinical", "Human Resource": "Non-Clinical",
    "Information Technology": "Non-Clinical", "Medical Admin Office": "Non-Clinical",
    "Operations": "Non-Clinical",
}

PROFILES = {  # designation mix per leaf
    "nurse": {"Staff Nurse": 0.92, "Executive": 0.08},
    "nurse_mostly": {"Staff Nurse": 0.70, "Executive": 0.30},
    "nurse_admin": {"Staff Nurse": 0.35, "Executive": 0.65},
    "mixed": {"Staff Nurse": 0.50, "Executive": 0.50},
    "exec": {"Executive": 1.0},
    "pharm": {"Pharmacist": 0.85, "Executive": 0.15},
    "pharm_exec": {"Pharmacist": 0.30, "Executive": 0.70},
}

# (Department, Division, Sub Division, Location, profile, headcount weight)
LEAVES = [
    ("Cardiology", "Cardiology", "Cardiology", "Cardiology", "nurse_mostly", 10),
    ("Cardiology", "Cardiology", "Cath Lab", "Cath Lab", "nurse", 8),
    ("Clinical Nursing", "Clinical Nursing", "Casualty", "Casualty", "nurse", 12),
    ("Clinical Nursing", "Clinical Nursing", "Operation Theatre", "Operation Theatre", "nurse", 14),
    ("Clinical Nursing", "Clinical Nursing", "Dialysis", "Dialysis", "nurse", 6),
    ("Clinical Nursing", "Clinical Nursing", "Labour Ward", "Labour Ward", "nurse", 8),
    ("Clinical Nursing", "Critical Care", "CTICU", "CTICU", "nurse", 8),
    ("Clinical Nursing", "Critical Care", "ICU", "ICU", "nurse", 12),
    ("Clinical Nursing", "Critical Care", "MICU", "MICU", "nurse", 8),
    ("Clinical Nursing", "Critical Care", "SICU", "SICU", "nurse", 8),
    ("Clinical Nursing", "Critical Care", "NICU", "NICU", "nurse", 7),
    ("Clinical Nursing", "Ward", "Ward", "Ward - 2nd Floor", "nurse", 10),
    ("Clinical Nursing", "Ward", "Ward", "Ward - 3rd Floor", "nurse", 10),
    ("Clinical Nursing", "Ward", "General Ward", "General Ward", "nurse", 8),
    ("Clinical Nursing", "Ward", "General Ward", "General Ward III Floor", "nurse", 8),
    ("Clinical Nursing", "Ward", "General Ward", "General Ward IV Floor", "nurse", 8),
    ("Clinical Nursing", "Ward", "Deluxe Ward", "Deluxe Ward V Floor", "nurse", 6),
    ("Clinical Nursing", "Ward", "Special Ward", "Special Ward V Floor", "nurse", 6),
    ("Clinical Nursing", "Nursing", "Nursing", "Nursing", "nurse", 6),
    ("Clinical Nursing", "Nursing", "Nursing Admin", "Nursing Admin", "nurse_admin", 3),
    ("Clinical Nursing", "Nursing", "Nursing- MOD", "Nursing- MOD", "nurse_mostly", 3),
    ("Clinical Nursing", "Anesthesia", "Anesthesia", "Anesthesia", "nurse", 5),
    ("Clinical Nursing", "Endoscopy", "Endoscopy", "Endoscopy", "nurse", 4),
    ("Clinical Nursing", "General Surgery", "General Surgery", "General Surgey", "nurse", 5),
    ("Clinical Nursing", "Neuro Surgery", "Neuro Surgery", "Neuro Surgery", "nurse", 5),
    ("Clinical Nutrition & Dietetics", "Patient Service", "Clinical Nutrition & Dietetics", "Clinical Nutrition & Dietetics", "exec", 4),
    ("Clinical Nutrition & Dietetics", "Patient Service", "Food & Beverages", "Food & Beverages", "exec", 8),
    ("Clinical Nutrition & Dietetics", "Patient Service", "Patient Service", "Front Office", "exec", 3),
    ("Curtis", "Curtis", "Curtis", "Curtis", "mixed", 6),
    ("Clinical Support", "Blood Bank", "Blood Bank", "Blood Bank", "mixed", 3),
    ("Clinical Support", "HIC", "HIC", "HIC", "nurse_mostly", 2),
    ("Clinical Support", "HIC", "CSSD", "CSSD", "nurse_mostly", 4),
    ("Clinical Support", "OHC", "OHC", "OHC", "mixed", 3),
    ("Clinical Support", "OHC", "Physiotherapy", "Physiotherapy", "exec", 4),
    ("Biomedical", "Engineering", "Biomedical Engineering", "Biomedical Engineering", "exec", 5),
    ("Lab", "Lab", "Lab", "Lab", "exec", 14),
    ("Lab", "Lab", "Radiology", "Radiology", "exec", 8),
    ("Pharmacy", "Pharmacy", "Pharmacy", "Pharmacy", "pharm", 6),
    ("Pharmacy", "Pharmacy", "IP Pharmacy", "IP Pharmacy", "pharm", 8),
    ("Pharmacy", "Pharmacy", "OP Pharmacy", "OP Pharmacy", "pharm", 8),
    ("Pharmacy", "Pharmacy", "OT Pharmacy", "OT Pharmacy", "pharm", 5),
    ("Pharmacy", "Pharmacy", "Pharmacy Purchase", "Pharmacy Purchase", "pharm_exec", 3),
    ("Pharmacy", "Clinical Pharmacology", "Clinical Pharmacology", "Clinical Pharmacology", "pharm_exec", 2),
    ("Administrative Office", "Administrative Office", "Administrative Office", "Administrative Office", "exec", 4),
    ("Branding", "Branding", "Branding", "Branding", "exec", 3),
    ("Business Development", "Business Development", "Business Development", "Business Development", "exec", 4),
    ("Business Development", "Business Development", "Corporate Sales", "Corporate Sales", "exec", 3),
    ("Business Development", "Business Development", "International Marketing", "International Marketing", "exec", 3),
    ("Facility Services", "Facility Services", "Facility Services", "Facility Services", "exec", 6),
    ("Facility Services", "Facility Services", "Facility Engineering", "Facility Engineering", "exec", 4),
    ("Finance and Accounts", "Finance And Accounts", "Unit Finance and Accounts", "Unit Finance and Accounts", "exec", 6),
    ("Finance and Accounts", "Finance And Accounts", "TPA", "TPA", "exec", 4),
    ("Finance and Accounts", "Biling", "Biling", "Billing", "exec", 8),
    ("Finance and Accounts", "Biling", "IP Billing", "IP Billing", "exec", 6),
    ("Finance and Accounts", "Business Office", "Business Office", "Business Office", "exec", 4),
    ("Finance and Accounts", "Purchase", "Unit Purchase", "Unit Purchase", "exec", 4),
    ("Human Resource", "Human Resources", "Unit HR", "Unit HR", "exec", 4),
    ("Information Technology", "Information Technology", "Information Technology", "Information Technology", "exec", 5),
    ("Information Technology", "Telecommunication", "Telecommunication", "Telecommunication", "exec", 3),
    ("Medical Admin Office", "Medical Services", "Medical Admin Office", "Medical Admin Office", "exec", 3),
    ("Medical Admin Office", "Medical Services", "Medical Services", "Medical Services", "exec", 3),
    ("Medical Admin Office", "Medical Services", "ED Office", "ED Office", "exec", 2),
    ("Medical Admin Office", "Medical Services", "Manager on Duty", "Manager on Duty", "nurse_admin", 2),
    ("Medical Admin Office", "MRD", "MRD", "MRD", "exec", 5),
    ("Medical Admin Office", "MRD", "MRD", "Medical Transcriptionist", "exec", 3),
    ("Operations", "Operations", "Operations", "Operations", "exec", 4),
    ("Operations", "IP Services", "IP Services", "IP Services", "exec", 4),
    ("Operations", "OPD", "OPD", "OPD", "mixed", 10),
    ("Operations", "Out Patient Services", "General OP", "General OP", "mixed", 8),
    ("Operations", "Out Patient Services", "Front Office", "Front Office", "exec", 5),
    ("Operations", "Business Excellence", "Quality", "Quality", "exec", 3),
    ("Operations", "Business Excellence", "Service Excellence", "Service Excellence", "exec", 3),
    ("Operations", "Business Excellence", "Service Line Manager", "Service Line Manager", "exec", 2),
]

FEMALE_SHARE = {"Staff Nurse": 0.86, "Pharmacist": 0.55, "Executive": 0.42}
JOIN_AGE_SCALE = {"Staff Nurse": 2.5, "Pharmacist": 2.8, "Executive": 4.0}
SALARY_START = {"Staff Nurse": (14000, 20000), "Pharmacist": (18000, 26000), "Executive": (16000, 30000)}
P_GRADE_4A = {"Staff Nurse": 0.20, "Pharmacist": 0.50, "Executive": 0.55}

FEMALE_FIRST = """Anitha Divya Priya Deepa Lakshmi Meera Sindhu Reshma Sruthi Anju Neethu Aswathy Athira
Remya Sreeja Jisha Bincy Soumya Kavitha Revathi Nisha Shalini Swathi Pooja Sneha Anjali Gayathri Malavika
Lekha Nimmy Jincy Ancy Merin Elizabeth Sarah Preethi Vidya Harini Keerthana Ramya Nandhini Sowmya Bhavya
Aparna Lija Dhanya Rekha Sheeba Sunitha Jaya Usha Radhika Manju Sangeetha Thulasi Fathima Ayesha Shabana
Rukhsana Mary Betsy Teena Ria Sherin""".split()
MALE_FIRST = """Arun Rahul Vishnu Manoj Suresh Ramesh Anil Sajeev Biju Jithin Akhil Abhilash Anoop Sanjay Vijay
Prakash Kiran Mohan Ganesh Karthik Harish Naveen Praveen Sreejith Rajesh Sunil Thomas George Joseph Jacob
Mathew Basil Ajay Deepak Dinesh Gopal Hari Krishnan Mahesh Murali Prasad Rajan Satish Shyam Sivan Unni Varun
Vinod Yusuf Imran Faisal Riyas Shafeeq Nazar Salim Arjun Adithya Aravind Ashwin Robin Tijo Jomon Sabu Shiju""".split()
FEMALE_SECOND = ["Mary", "Devi", "Priya", "Ann", "Rani", "Kumari"]
MALE_SECOND = ["Kumar", "Raj", "Krishna", "Mathew", "Babu", "Joseph", "Prasad"]
INITIAL_LETTERS = "AKMPRSTVJNBGCDL"


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


class Resolver:
    """Map a loosely typed name to the template's exact spelling for a column."""

    def __init__(self, cats):
        self.maps = {}
        for col, vals in cats.items():
            m = {norm(v): v for v in vals}
            assert len(m) == len(vals), f"'{col}' has values that differ only by whitespace/case"
            self.maps[col] = m

    def __call__(self, col, name):
        try:
            return self.maps[col][norm(name)]
        except KeyError:
            raise KeyError(f"'{name}' is not a value in template column '{col}'") from None


def load_template(path):
    ws = load_workbook(path).active
    headers = [c.value for c in ws[1]]
    cats = {}
    for idx, h in enumerate(headers, start=1):
        if h not in CATEGORY_COLUMNS:
            continue
        vals = []
        for r in range(2, ws.max_row + 1):
            v = ws.cell(r, idx).value
            if v is not None and v not in vals:
                vals.append(v)
        cats[h] = vals
    return ws.title, headers, cats


def ccenter_for(dept, sub):
    if norm(sub) == "food & beverages":
        return "Canteen"
    if norm(sub) == "ohc":
        return "OHC"
    if norm(dept) == "pharmacy" and norm(sub) != "clinical pharmacology":
        return "Kmeds"
    return "Unit"


def build_rows(cats, n, seed, today):
    rng = random.Random(seed)
    R = Resolver(cats)
    if n < len(LEAVES):
        raise ValueError(f"--rows must be at least {len(LEAVES)} so every category appears once")

    # one row per leaf guarantees every category value appears; the rest follow the weights
    leaf_rows = list(LEAVES) + rng.choices(LEAVES, weights=[l[5] for l in LEAVES], k=n - len(LEAVES))
    rng.shuffle(leaf_rows)
    new_joiners = set(rng.sample(range(n), 8))  # guarantee some joiners in the last 30 days

    emps = []
    for i, (dept, div, sub, loc, profile, _w) in enumerate(leaf_rows):
        prof = PROFILES[profile]
        desig = rng.choices(list(prof), weights=list(prof.values()))[0]
        gender = "Female" if rng.random() < FEMALE_SHARE[desig] else "Male"
        while True:
            tenure = rng.uniform(1, 29) / 365.25 if i in new_joiners else rng.expovariate(1 / 5.0)
            join_age = 21 + min(rng.gammavariate(2.0, JOIN_AGE_SCALE[desig]), 22)
            if tenure <= 26 and join_age + tenure <= 60:
                break
        doj = today - timedelta(days=int(tenure * 365.25))
        dob = doj - timedelta(days=int(join_age * 365.25))
        first = rng.choice(FEMALE_FIRST if gender == "Female" else MALE_FIRST)
        if rng.random() < 0.35:
            first += " " + rng.choice(FEMALE_SECOND if gender == "Female" else MALE_SECOND)
        initial = "".join(rng.choice(INITIAL_LETTERS) for _ in range(1 if rng.random() < 0.72 else 2))
        emps.append(dict(
            dept=R("Department", dept), div=R("Division", div), sub=R("Sub Division", sub),
            loc=R("Location", loc), group=R("Department Group", GROUP_OF_DEPT[dept]),
            desig=R("Designation", desig), gender=gender, name=first, initial=initial,
            dob=dob, doj=doj, left=None,
            ccenter=R("Ccenter", ccenter_for(dept, sub)),
        ))

    # leavers: ~12%, skewed toward recent exits, plus a few guaranteed in the last 60 days
    eligible = [i for i, e in enumerate(emps) if (today - e["doj"]).days >= 150 and i not in new_joiners]
    for k, i in enumerate(rng.sample(eligible, round(0.12 * n))):
        e = emps[i]
        lo = e["doj"] + timedelta(days=90)
        if k < 6:
            e["left"] = today - timedelta(days=rng.randint(3, 60))
        else:
            span = (today - lo).days
            e["left"] = lo + timedelta(days=int(span * rng.betavariate(1.3, 1.0)))

    # Empno ascends with DOJ, like a real HRMS export
    emps.sort(key=lambda e: (e["doj"], rng.random()))
    empno = 10000
    for e in emps:
        empno += rng.choice([1, 1, 1, 2, 3])
        e["empno"] = empno

    # salary, grade, group stage, status
    g_hi, g_lo = R("Grade", "4A"), R("Grade", "5C")
    grp7, grp5 = R("Group Stage", "Group 7"), R("Group Stage", "Group 5")
    for e in emps:
        d = e["desig"]
        e["grade"] = g_hi if rng.random() < P_GRADE_4A[d] else g_lo
        e["stage"] = grp7 if rng.random() < 0.35 else grp5
        yrs = ((e["left"] or today) - e["doj"]).days / 365.25
        basic = rng.uniform(*SALARY_START[d]) * (1.06 ** min(yrs, 15))
        basic *= 1.10 if e["grade"] == g_hi else 1.0
        basic *= 1.12 if e["stage"] == grp7 else 1.0
        basic *= rng.uniform(0.95, 1.05)
        e["basic"] = int(round(basic / 100) * 100)
        e["gross"] = int(round(e["basic"] * rng.uniform(1.30, 1.65) / 100) * 100)
        recent = (today - e["doj"]).days < 365
        e["status"] = R("Status", "waiting") if rng.random() < (0.60 if recent else 0.10) else R("Status", "Entry Level")

    # reporting line: sub-division head -> division head -> department head -> global head
    active = [e for e in emps if e["left"] is None]
    by_sub, by_div, by_dept = defaultdict(list), defaultdict(list), defaultdict(list)
    for e in active:
        by_sub[(e["dept"], e["div"], e["sub"])].append(e)
        by_div[(e["dept"], e["div"])].append(e)
        by_dept[e["dept"]].append(e)
    head = lambda grp: min(grp, key=lambda x: x["empno"]) if grp else None
    global_head = head(by_dept[R("Department", "Administrative Office")])
    for e in emps:
        chain = []
        g = by_sub[(e["dept"], e["div"], e["sub"])]
        if len(g) >= 4:
            chain.append(head(g))
        chain.append(head(by_div[(e["dept"], e["div"])]))
        chain.append(head(by_dept[e["dept"]]))
        chain.append(global_head)
        sup = next((s for s in chain if s is not None and s["empno"] != e["empno"]), None)
        e["reports_to"] = f'{sup["empno"]} {sup["name"]}' if sup else None

    smiley, category = R("Left", "Smiley"), R("Category", "Onroll")
    punit, wunit = R("Punit", "KMH"), R("Wunit", "KMH")
    rows = []
    for sno, e in enumerate(emps, start=1):
        rows.append({
            "EE": None, "Sno": sno, "Empno.": e["empno"], "Name": e["name"], "Initial": e["initial"],
            "Gender": e["gender"], "Department Group": e["group"], "Department": e["dept"],
            "Division": e["div"], "Sub Division": e["sub"], "Location": e["loc"],
            "Designation": e["desig"], "Grade": e["grade"], "DOB": e["dob"], "DOJ": e["doj"],
            "Group Stage": e["stage"], "Basic + DA": e["basic"], "Fixed Gross": e["gross"],
            "Reporting to": e["reports_to"], "Category": category, "Ccenter": e["ccenter"],
            "Punit": punit, "Wunit": wunit, "Left": e["left"] if e["left"] else smiley,
            "Status": e["status"],
        })
    return rows


def check_coverage(rows, cats):
    problems = []
    for col, vals in cats.items():
        if col == "Left":  # 'DATE(If left)' is a description, not a literal value
            continue
        missing = [v for v in vals if v not in {r[col] for r in rows}]
        if missing:
            problems.append((col, missing))
    if problems:
        raise AssertionError(f"Template values never used: {problems}")


def write_workbook(path, sheet_title, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    base = Font(name="Arial", size=10)
    head_font = Font(name="Arial", size=10, bold=True)
    head_fill = PatternFill("solid", start_color="D9E1F2")
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(1, c, h)
        cell.font, cell.fill = head_font, head_fill
        cell.alignment = Alignment(horizontal="center")
    for r, row in enumerate(rows, start=2):
        for c, h in enumerate(headers, start=1):
            v = row.get(h)
            cell = ws.cell(r, c, v)
            cell.font = base
            if isinstance(v, date):
                cell.number_format = "DD-MM-YYYY"
            elif h in ("Basic + DA", "Fixed Gross"):
                cell.number_format = "#,##0"
    for c, h in enumerate(headers, start=1):
        longest = max([len(str(h))] + [len(str(r.get(h) or "")) for r in rows])
        ws.column_dimensions[get_column_letter(c)].width = min(max(longest + 2, 8), 40)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default="employee records.xlsx")
    ap.add_argument("--out", default="employee_records_dummy.xlsx")
    ap.add_argument("--rows", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today(),
                    help="reference date for tenure/exit dates (YYYY-MM-DD)")
    a = ap.parse_args()

    title, headers, cats = load_template(a.template)
    rows = build_rows(cats, a.rows, a.seed, a.today)
    check_coverage(rows, cats)
    write_workbook(a.out, title, headers, rows)
    print(f"Wrote {len(rows)} rows x {len(headers)} columns to {a.out}")


if __name__ == "__main__":
    main()