# ingestion.py

import duckdb
import hashlib
from pathlib import Path
from datetime import datetime
import logging
from config import settings
import pandas as pd

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
    return conn



def setup_tables(conn):
    # create ingestion_audit table if not exists
    # columns: id, filename, md5_hash, loaded_at, status
    # create dim_employees table if not exists
    # create fact_payroll table if not exists
    # create fact_gl table if not exists
    conn.execute("CREATE TABLE IF NOT  EXISTS ingestion_audit(id INTEGER,filename VARCHAR,md5_hash VARCHAR,loaded_at DATE,status VARCHAR)")

    conn.execute("CREATE TABLE IF NOT  EXISTS dim_employees(Employee_ID  VarCHAR,Employee_Name  VARCHAR,Department  VARCHAR,Designation VARCHAR,Category  VARCHAR,Date_Of_Joining  DATE,Date_Of_Leaving  DATE,Employment_Status VARCHAR,Base_Salary_HRIS FLOAT,Bank_Name VARCHAR,Bank_Account VARCHAR,UAN_Number VARCHAR,PAN_Number VARCHAR,Location VARCHAR)")
    
    conn.execute("CREATE TABLE IF NOT  EXISTS fact_payroll(Employee_ID VARCHAR,Employee_Name VARCHAR,Department VARCHAR,Pay_Period DATE,Base_Salary_Payroll FLOAT,Basic_salary FLOAT,HRA FLOAT,DA FLOAT,Transport_Allowance FLOAT, Medical_Allowance FLOAT,Special_Allowance FLOAT,Overtime FLOAT,Gross_Pay FLOAT,PF_deduction FLOAT,ESI_deduction FLOAT,TDS_deduction FLOAT,PT_deduction FLOAT,Loan_deduction FLOAT,Total_deductions FLOAT,Net_pay FLOAT,Payment_Mode VARCHAR,Payment_Status VARCHAR,Payroll_Run_ID VARCHAR,Remarks VARCHAR)")

    conn.execute("CREATE TABLE IF NOT EXISTS fact_gl(GL_Entry_ID VARCHAR,Employee_ID VARCHAR,Department VARCHAR,Pay_Period date,GL_Account_Code VARCHAR, GL_Amount_Posted FLOAT,Payroll_Net_Pay_Reference FLOAT,Posting_Date DATE,Posted_By VARCHAR,GL_Remarks VARCHAR)")

    

    

def is_duplicate(conn, filehash: str) -> bool:
    # query ingestion_audit for this hash
    # return True if found, False if not
    dupl=conn.execute("SELECT md5_hash FROM ingestion_audit WHERE md5_hash = ? ",[filehash]).fetchone()
    if dupl is None:
        return False
    else:
        return True

    

def record_ingestion(conn, filename: str, md5_hash: str, status: str):
    # insert a row into ingestion_audit
    audit_row={"file_name":filename,"md5_hash":md5_hash,"Status":status}
    conn.execute("INSERT INTO ingestion_audit (filename,md5_hash,loaded_at,status) VALUES (?,?,?,?)",[filename,md5_hash,datetime.today(),status])
    return conn,audit_row


def load_records(conn, feedtype: str, valid_rows: list):
    # based on feedtype, insert valid_rows into the right table
    # dim_employees for hris_export
    # fact_payroll for payroll_register
    # fact_gl for gl_dump

    row_data={"file_name":feedtype,"valid_rows":valid_rows}
    valid_rows=pd.DataFrame(valid_rows)
    

    if feedtype =="hris_export":
        #change comparison as required based on file name 
        try:
            conn.execute("INSERT INTO dim_employees SELECT * FROM  valid_rows")
        except Exception as e:
            row_data=f"error:{e}"
            return(conn,row_data)

    elif feedtype =="payroll_register":
        #change comparison as required based on file name 
        try:
            conn.execute("INSERT INTO fact_payroll SELECT * FROM valid_rows")

        except Exception as e:
            row_data=f"error:{e}"
            return(conn,row_data)

    elif feedtype =="gl_dump":
        #change comparison as required based on file name 
        try:
            conn.execute("INSERT INTO fact_gl SELECT * FROM valid_rows")
        except Exception as e:
            row_data=f"error:{e}"
            return(conn,row_data)
    return conn,row_data

def run_ingestion(file_path: Path, valid_rows: list,feedtype:str):
    # 1. compute md5
    # 2. connect to DB
    # 3. setup tables
    # 4. check if duplicate — if yes, log and return
    # 5. load records
    # 6. record in ingestion_audit with status "loaded"
    conn=get_connection(settings.database_path)
    setup_tables(conn)
    md5_hash=file_md5(file_path)
    file_duplicate=is_duplicate(conn,md5_hash)
    ingest={"audit_row":None,"row_data":None}
    if file_duplicate:
            msg="file already uploaded/run by the pipeline"
            audit_logger.error(f"{msg}")
            print(f"{msg}")
            ingest["audit_row"]=msg
            ingest["row_data"]=msg
            return ingest


    else:
        try:
            conn.execute("BEGIN TRANSACTION")
            conn,audit_row=record_ingestion(conn,feedtype,md5_hash,status="loaded")
            conn,row_data=load_records(conn,feedtype,valid_rows)
            conn.execute("COMMIT")
            ingest["audit_row"]=audit_row
            ingest["row_data"]=row_data
            return (ingest)
        

        except Exception as e:
            conn.execute("ROLLBACK")
            msg="database writting failed in ingestion"
            logger.error(f"{msg}")
            print(f"{msg}")
            ingest["audit_row"]=msg
            ingest["row_data"]=msg
            return ingest
        
    

    