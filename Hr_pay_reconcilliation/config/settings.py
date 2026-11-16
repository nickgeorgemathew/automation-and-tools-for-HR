# config/settings.py
from pathlib import Path

# Project root. Assumes this file lives at <root>/config/settings.py.
BASE_DIR = Path(__file__).resolve().parent.parent

# -- Paths (absolute, so they no longer depend on where Streamlit is launched) --
incoming_feeds = str(BASE_DIR / "src" / "data" / "incoming_feeds")
database_path = str(BASE_DIR / "src" / "data" / "dim_employees.db")
quarentine_path = str(BASE_DIR / "src" / "data" / "quarentine")
output_path = str(BASE_DIR / "output")

# -- Feed file names: WITH the extension. validator.py compares them to file_path.name,
#    run_main() globs "*.csv", and the Overview page saves uploads under these names. --
name_payroll = "payroll_register.csv"
name_hris = "hris_export.csv"
name_gl = "gl_dump.csv"

# -- Allowed values for row validation (copied from mock_generator.py).
#    For real data, take these lists from HR, not from the generator. --
department = [
    "Emergency", "ICU", "General_Ward", "OPD", "Surgery",
    "Radiology", "Pathology", "Pharmacy", "Admin", "HR",
    "Housekeeping", "Security", "Accounts", "IT", "Canteen",
]
designation = [
    "Senior_Consultant", "Junior_Resident_Doctor", "Head_Nurse", "Staff_Nurse", "ANM",
    "Radiographer", "Lab_Technician", "Physiotherapist", "Pharmacist",
    "HR_Manager", "HR_Executive", "Accounts_Officer", "IT_Support", "Admin_Executive",
    "Housekeeping_Staff", "Security_Guard", "Canteen_Staff", "Driver",
]
category = ["Clinical", "Nursing", "Allied_Health", "Admin", "Support"]
Allowed_Employment_Status = ["Active", "Terminated", "On_Leave"]
location = ["Main_Campus", "Branch_Koramangala", "Branch_Whitefield"]

# -- Thresholds. These must be real values: a 0 here is not "unset", it is a threshold of 0. --
amount_tolerance = 0.1          # rupees; used when comparing two money values
MoM_variance_percentage = 0.15  # 15%; check_mom_variance does not read this yet
OT_limit = 0.25                 # overtime above 25% of base salary is flagged
ESI_wage_boundary = 21000       # verify against the current statutory limit
ESI_band = 3000                 # how far below the limit counts as "near"
ot_z_threshold = 1.5            # Z-score cut-off for department overtime hotspots

overtime_eligible = []