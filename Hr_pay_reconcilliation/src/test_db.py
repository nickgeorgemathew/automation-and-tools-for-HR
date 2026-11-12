import duckdb
from config import settings
import pandas as pd
from enum import Enum
from dataclasses import dataclass


db_path=settings.database_path
conn=duckdb.connect(db_path)



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


pay_period="10/2026"

hris_file="C:/Users/nikhi/Downloads/automation-and-tools-for-HR/Hr_pay_reconcilliation/src/data/incoming_feeds/hris_export.csv"
hris_file=pd.read_csv(hris_file)
payroll_file="src/data/incoming_feeds/payroll_register.csv"
payroll_file=pd.read_csv(payroll_file)
gl_file="src/data/incoming_feeds/gl_dump.csv"
gl_file=pd.read_csv(gl_file)

result=conn.execute("CREATE TABLE IF NOT  EXISTS dim_employees(Employee_ID  VarCHAR,Employee_Name  VARCHAR,Department  VARCHAR,Designation VARCHAR,Category  VARCHAR,Date_Of_Joining  DATE,Date_Of_Leaving  DATE,Employment_Status VARCHAR,Base_Salary_HRIS FLOAT,Bank_Name VARCHAR,Bank_Account VARCHAR,UAN_Number VARCHAR,PAN_Number VARCHAR,Location VARCHAR)").fetchall()
result=conn.execute("INSERT INTO dim_employees SELECT * FROM hris_file").fetchall()
result=conn.execute("SELECT * FROM dim_employees").fetchall()

conn.execute("CREATE TABLE IF NOT  EXISTS ingestion_audit(id INTEGER,filename VARCHAR,md5_hash VARCHAR,loaded_at DATE,status VARCHAR)")
    
conn.execute("CREATE TABLE IF NOT  EXISTS fact_payroll(Employee_ID VARCHAR,Employee_Name VARCHAR,Department VARCHAR,Pay_Period DATE,Base_Salary_Payroll FLOAT,Basic_salary FLOAT,HRA FLOAT,DA FLOAT,Transport_Allowance FLOAT, Medical_Allowance FLOAT,Special_Allowance FLOAT,Overtime FLOAT,Gross_Pay FLOAT,PF_deduction FLOAT,ESI_deduction FLOAT,TDS_deduction FLOAT,PT_deduction FLOAT,Loan_deduction FLOAT,Total_deductions FLOAT,Net_pay FLOAT,Payment_Mode VARCHAR,Payment_Status VARCHAR,Payroll_Run_ID VARCHAR,Remarks VARCHAR)")

result=conn.execute("INSERT INTO fact_payroll SELECT * FROM payroll_file").fetchall()

conn.execute("CREATE TABLE IF NOT EXISTS fact_gl(GL_Entry_ID VARCHAR,Employee_ID VARCHAR,Department VARCHAR,Pay_Period date,GL_Account_Code VARCHAR, GL_Amount_Posted FLOAT,Payroll_Net_Pay_Reference FLOAT,Posting_Date DATE,Posted_By VARCHAR,GL_Remarks VARCHAR)")

result=conn.execute("INSERT INTO fact_gl SELECT * FROM gl_file").fetchall()


rows = conn.execute("""
            SELECT e.Employee_ID,e.Date_of_Leaving,e.Employment_Status,p.Pay_Period,p.Payment_Status,p.Net_pay  FROM dim_employees AS e JOIN fact_payroll AS p ON e.Employee_ID = p.Employee_ID  WHERE p.Pay_period =? AND  p.Pay_Period > e.Date_of_Leaving AND e.Date_of_Leaving IS NOT Null
        """, [pay_period]).fetchall()
findings=[Finding(ErrorType.CRITICAL_TERMINATED_PAID, "CRITICAL", emp, pay_period,
                        None, net, f"{emp} has exited but has been paid")for emp, net in rows]

print(findings)


print(result)