import os
incoming_feeds="src/data/incoming_feeds"
database_path="src/data/dim_employees.db"
name_payroll="payroll_register"
name_hris="hris_export"
name_gl="gl_dump"
quarentine_path="Hr_pay_reconcilliation/quarentine"
tolerance=0.1
esi_boundary=25000
overtime_eligible=[]
# config/settings.py
payroll_cols = [
    "Employee_ID","Employee_Name","Department","Pay_Period",
    "Base_Salary_Payroll","Net_Pay","Payroll_Run_ID"
]

hris_cols = [
    "Employee_ID","Employee_Name","Department","Date_Of_Joining",
    "Employment_Status","Base_Salary_HRIS"
]

gl_cols = [
    "GL_Entry_ID","Employee_ID","Department","Pay_Period",
    "GL_Account_Code","GL_Amount_Posted","Payroll_Net_Pay_Reference"
]

EXPECTED_COLUMNS = {
    "payroll_register": payroll_cols,
    "hris_export": hris_cols,
    "gl_dump": gl_cols,
}

department=[]
designation=[]
category=[]
Allowed_Employment_Status=[]
location=[]
MoM_variance_percentage=0
OT_limit=0
ESI_wage_boundary=0
amount_tolerance=0