import os
name_payroll="payroll_register"
name_hris="hris_export"
name_gl="gl_dump"
quarentine_path="Hr_pay_reconcilliation/quarentine"
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