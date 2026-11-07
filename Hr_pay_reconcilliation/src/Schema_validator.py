from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from config import settings
import logging


"""Change the col names according to the files being used,implement flexible or find actual column names"""

logger=logging.getLogger("pipeline")

class HRISRecord(BaseModel):
    Employee_ID: str
    Employee_Name: str
    Department: str
    Designation: str
    Category: str
    Date_Of_Joining: datetime
    Date_Of_Leaving: Optional[datetime] = None
    Employment_Status: str
    Base_Salary_HRIS: float
    Bank_Name: str
    Bank_Account: str
    UAN_Number: str
    PAN_Number: str
    Location: str

    @field_validator('Employee_ID')
    def employee_id_fix(cls,v):
        if not v[:].isdigit():
            logger.error("Employee ID is not Valid,must be digits")
            raise ValueError("Employee ID is not Valid,must be digits")
        return v


    @field_validator('Department')
    def employee_name(cls,v):
        if v not in settings.department:
            logger.error("department is not valid")
            raise ValueError("Department is not valid")
        return v

    @field_validator('Designation')
    def designation(cls,v):
        if v not in settings.designation:
            logger.error("designation is not valid")
            raise ValueError("Designation is not valid")
        return v


    @field_validator('Category')
    def category(cls,v):
        if v not in settings.category:
            logger.error("Category is not valid")
            raise ValueError("Category is not valid")
        return v

    @field_validator('Date_Of_Joining')
    def Date_of_joining(cls,v):
        if v > datetime.today():
            logger.error("Date is not valid")  
            raise ValueError("Date is not valid")          
        return v
    @field_validator('Employment_Status')
    def employement_status(cls,v):
        if v not in settings.Allowed_Employment_Status:
            logger.error("Employment status is not valid")
            raise ValueError("Employment status is not valid")
        

        



class FinanceLedger(BaseModel):
     GL_Entry_ID:str
     Employee_ID:str
     Department:str
     Pay_Period:datetime
     GL_Account_Code:str
     GL_Amount_Posted:float
     Payroll_Net_Pay_Reference:float
     Posting_Date:datetime
     Posted_By:str
     GL_Remarks:Optional[str] = None


class PayrollRegister(BaseModel):
    Employee_ID:str
    Employee_Name:str
    Department:str
    Pay_Period:datetime
    Base_Salary_Payroll:float
    Basic_salary:float
    HRA:float
    DA:float
    Transport_Allowance:Optional[float]= None
    Medical_Allowance:float
    Special_Allowance:float
    Overtime:float
    Gross_Pay:float
    PF_Deduction:float
    ESI_Deduction:float
    TDS_Deduction:float
    PT_Deduction:float
    Loan_deduction:float
    Total_Deductions:float
    Net_pay:float
    Payment_Mode:str
    Payment_Status:str
    Payroll_Run_ID:str