import duckdb
from config import settings
import pandas as pd

db_path=settings.database_path
conn=duckdb.connect(db_path)

gl_file="C:/Users/nikhi/Downloads/automation-and-tools-for-HR/Hr_pay_reconcilliation/src/data/incoming_feeds/hris_export.csv"
gl_file=pd.read_csv(gl_file)
result=conn.execute("CREATE TABLE IF NOT  EXISTS dim_employees(Employee_ID  VarCHAR,Employee_Name  VARCHAR,Department  VARCHAR,Designation VARCHAR,Category  VARCHAR,Date_Of_Joining  DATE,Date_Of_Leaving  DATE,Employment_Status VARCHAR,Base_Salary_HRIS FLOAT,Bank_Name VARCHAR,Bank_Account VARCHAR,UAN_Number VARCHAR,PAN_Number VARCHAR,Location VARCHAR)").fetchall()
result=conn.execute("INSERT INTO dim_employees SELECT * FROM gl_file").fetchall()
result=conn.execute("SELECT * FROM dim_employees").fetchall()

print(result)