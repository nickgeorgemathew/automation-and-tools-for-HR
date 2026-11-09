# ingestion.py

import duckdb
import hashlib
from pathlib import Path
from datetime import datetime
import logging
from config import settings


# 1. Initialize your custom loggers
logger = logging.getLogger("pipeline")
audit_logger = logging.getLogger("audit")

# Set their individual tracking levels

audit_logger.setLevel(logging.INFO)

# 2. CRITICAL: Stop logs from bubbling up to the default console handler
logger.propagate = False
audit_logger.propagate = False

p_handler = logging.FileHandler("logs/pipeline_errors.log")
p_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(p_handler)
# Handler for "audit" -> audit.log
a_handler = logging.FileHandler("logs/ingestion_audit.log")
a_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
audit_logger.addHandler(a_handler)



def file_md5(path: Path) -> str:
    # read file in binary, compute MD5, return hex string
    #compare between MD5 and SHA 256 and choose which is the best one
    with open(path,"rb") as f:
        digest=hashlib.file_digest(f,"md5")
    md5_hash=digest.hexdigest()
    return md5_hash
    



def get_connection(db_path: Path):
    # connect to DuckDB at db_path
    conn=duckdb.connect(db_path)
    conn.execute("CREATE TABLE IF NOT  EXISTS test(id INTEGER)")
    return conn



def setup_tables(conn):
    # create ingestion_audit table if not exists
    # columns: id, filename, md5_hash, loaded_at, status
    # create dim_employees table if not exists
    # create fact_payroll table if not exists
    # create fact_gl table if not exists
    conn.execute("CREATE TABLE IF NOT  EXISTS file_md5_hash(id INTEGER,filename VARCHAR,md5_hash VARCHAR,loaded_at DATE,status VARCHAR)")

    conn.execute("CREATE TABLE IF NOT  EXISTS dim_employees(Employee_ID  VarCHAR,Employee_Name  VARCHAR,Department  VARCHAR,Designation VARCHAR,Category  VARCHAR,Date_Of_Joining  DATE,Date_Of_Leaving  DATE,Employment_Status VARCHAR,Base_Salary_HRIS FLOAT,Bank_Name VARCHAR,Bank_Account VARCHAR,UAN_Number VARCHAR,PAN_Number VARCHAR,Location VARCHAR)")
    
    conn.execute("CREATE TABLE IF NOT  EXISTS fact_payroll(Employee_ID VARCHAR,Employee_Name VARCHAR,Department VARCHAR,Pay_Period DATE,Base_Salary_Payroll FLOAT,Basic_salary FLOAT,HRA FLOAT,DA FLOAT,Transport_Allowance FLOAT, Medical_Allowance FLOAT,Special_Allowance FLOAT,Overtime FLOAT,Gross_Pay FLOAT,PF_Deduction FLOAT,ESI_Deduction FLOAT,TDS_Deduction FLOAT,PT_Deduction FLOAT,Loan_deduction FLOAT,Total_Deductions FLOAT,Net_pay FLOAT,Payment_Mode VARCHAR,Payment_Status VARCHAR,Payroll_Run_ID VARCHAR)")

    conn.execute("CREATE TABLE IF NOT EXISTS fact_gl(GL_Entry_ID VARCHAR,Employee_ID VARCHAR,Department VARCHAR,Pay_Period date,GL_Account_Code VARCHAR, GL_Amount_Posted FLOAT,Payroll_Net_Pay_Reference FLOAT,Posting_Date DATE,Posted_By VARCHAR,GL_Remarks VARCHAR)")

    result= conn.execute(" SELECT * FROM filehash").fetchall()

    return conn,result

def is_duplicate(conn, filehash: str) -> bool:
    # query ingestion_audit for this hash
    # return True if found, False if not
    dupl=conn.execute("SELECT md5_hash FROM file_md5_hash WHERE md5_hash = ? ",[filehash]).fetchone()
    if dupl is None:
        return False
    else:
        return True

def record_ingestion(conn, filename: str, md5_hash: str, status: str):
    # insert a row into ingestion_audit
    ##will use logger to log into the ingestion audit filefor now
    pass

def load_records(conn, feedtype: str, valid_rows: list, filename: str):
    # based on feedtype, insert valid_rows into the right table
    # dim_employees for hris_export
    # fact_payroll for payroll_register
    # fact_gl for gl_dump

    row_data={"file_name":filename,"valid_rows":valid_rows}

    if feedtype =="hris_export":
        #change comparison as required based on file name 
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("INSERT INTO dim_employees SELECT * FROM ? "[valid_rows])
        except Exception as e:
            conn.execute("ROLLBACK")

    elif feedtype =="payroll_register":
        #change comparison as required based on file name 
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("INSERT INTO fact_payroll SELECT * FROM ? "[valid_rows])
        except Exception as e:
            conn.execute("ROLLBACK")

    elif feedtype =="gl_dump":
        #change comparison as required based on file name 
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("INSERT INTO fact_gl SELECT * FROM ?"[valid_rows])
        except Exception as e:
            conn.execute("ROLLBACK")
    return conn,row_data

def run_ingestion(file_path: Path, valid_rows: list, feedtype: str):
    # 1. compute md5
    # 2. connect to DB
    # 3. setup tables
    # 4. check if duplicate — if yes, log and return
    # 5. load records
    # 6. record in ingestion_audit with status "loaded"
    pass