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
    @classmethod
    def employee_id_fix(cls,v):
        if not v[:].isdigit():
            logger.error("Employee ID is not Valid,must be digits")
            raise ValueError("Employee ID is not Valid,must be digits")
        return v

    @field_validator('Department')
    @classmethod
    def department_check(cls,v):
        if v not in settings.department:
            logger.error("Department is not valid")
            raise ValueError("Department is not valid")
        return v

    @field_validator('Designation')
    @classmethod
    def designation(cls,v):
        if v not in settings.designation:
            logger.error("Designation is not valid")
            raise ValueError("Designation is not valid")
        return v

    @field_validator('Category')
    @classmethod
    def category(cls,v):
        if v not in settings.category:
            logger.error("Category is not valid")
            raise ValueError("Category is not valid")
        return v

    @field_validator('Date_Of_Joining')
    @classmethod
    def date_of_joining(cls,v):
        if v > datetime.today():
            logger.error("Date Of Joining is not valid")  
            raise ValueError("Date Of Joining is not valid")          
        return v
    
    @field_validator('Employment_Status')
    @classmethod
    def employment_status(cls,v):
        if v not in settings.Allowed_Employment_Status:
            logger.error("Employment Status is not valid")
            raise ValueError("Employment Status is not valid")
        return v
        
    # @field_validator('Base_Salary_HRIS')
    # @classmethod
    # def base_salary_hris(cls,v):
    #         if v < 0:
    #             logger.error("Base Salary HRIS is not valid")  
    #             raise ValueError("Base Salary HRIS is not valid")          
    #         return v


    # @field_validator('Bank_Name')
    # @classmethod
    # def bank_name(cls,v):
    #         if not v or not str(v).strip():
    #             logger.error("Bank Name is not valid")  
    #             raise ValueError("Bank Name is not valid")          
    #         return v


    # @field_validator('Bank_Account')
    # @classmethod
    # def bank_account(cls,v):
    #         if not v or not str(v).strip():
    #             logger.error("Bank Account is not valid")  
    #             raise ValueError("Bank Account is not valid")          
    #         return v
        

    @field_validator('UAN_Number')
    @classmethod
    def uan_number(cls,v):
            if len(v) > 12:
                logger.error("UAN Number is not valid (Length greater than 12)")  
                raise ValueError("UAN Number is not valid(Length greater than 12)")
            elif len(v) < 12:
                logger.error("UAN Number is not valid (Length less than 12)")  
                raise ValueError("UAN Number is not valid(Length less than 12)")
            return v

    
    @field_validator('PAN_Number')
    @classmethod
    def pan_number(cls,v):
            if len(v)>10:
                logger.error("PAN Number is not valid(Length greater than 10)")  
                raise ValueError("PAN Number is not valid(Length greater than 10)")
            elif len(v)< 10:
                logger.error("PAN Number is not valid(Length less than 10)")  
                raise ValueError("PAN Number is not valid(Length less than 10)")          
            return v
            
    @field_validator('Location')
    @classmethod
    def location(cls,v):
            if v not in settings.location:
                logger.error("Location is not valid")  
                raise ValueError("Location is not valid")          
            return v


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
    
    @field_validator('Employee_ID')
    @classmethod
    def employee_id_fix(cls,v):
        if not v[:].isdigit():
            logger.error("Employee ID is not Valid,must be digits")
            raise ValueError("Employee ID is not Valid,must be digits")
        return v

    @field_validator('Department')
    @classmethod
    def department_check(cls,v):
        if v not in settings.department:
            logger.error("Department is not valid")
            raise ValueError("Department is not valid")
        return v
    
    @field_validator('Pay_Period')
    @classmethod
    def pay_period(cls,v):
        if v > datetime.today():
            logger.error("Pay Period is not valid")
            raise ValueError("Pay Period is not valid")
        return v

    @field_validator('GL_Account_Code')
    @classmethod
    def gl_account_code(cls,v):
        if not v or not str(v).strip():
            logger.error("GL Account Code is not valid")
            raise ValueError("GL Account Code is not valid")
        return v

    @field_validator('GL_Amount_Posted')
    @classmethod
    def gl_amount_posted(cls,v):
        if v < 0:
            logger.error("GL Amount Posted is less than 0")
            raise ValueError("GL Amount Posted is less than 0")
        return v

    @field_validator('Payroll_Net_Pay_Reference')
    @classmethod
    def payroll_net_pay_reference(cls,v):
        if v < 0:
            logger.error("Payroll Net Pay Reference is less than 0")
            raise ValueError("Payroll Net Pay Reference is less than 0")
        return v
   
    @field_validator('Posting_Date')
    @classmethod
    def posting_date(cls,v):
        if v > datetime.today():
            logger.error("Posting Date is not valid")
            raise ValueError("Posting Date is not valid")
        return v

    @field_validator('Posted_By')
    @classmethod
    def posted_by(cls,v):
        if not v or not str(v).strip():
            logger.error("Posted By is not valid")
            raise ValueError("Posted By is not valid")
        return v

    @field_validator('GL_Remarks')
    @classmethod
    def gl_remarks(cls,v):
        return v


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
    PF_deduction:float
    ESI_deduction:float
    TDS_deduction:float
    PT_deduction:float
    Loan_deduction:float
    Total_deductions:float
    Net_pay:float
    Payment_Mode:str
    Payment_Status:str
    Payroll_Run_ID:str

    @field_validator('Employee_ID')
    @classmethod
    def employee_id_fix(cls,v):
        if not v[:].isdigit():
            logger.error("Employee ID is not Valid,must be digits")
            raise ValueError("Employee ID is not Valid,must be digits")
        return v

    @field_validator('Employee_Name')
    @classmethod
    def employee_name(cls,v):
        if not v or not str(v).strip():
            logger.error("Employee Name is not valid")
            raise ValueError("Employee Name is not valid")
        return v

    @field_validator('Department')
    @classmethod
    def department_check(cls,v):
        if v not in settings.department:
            logger.error("Department is not valid")
            raise ValueError("Department is not valid")
        return v

    @field_validator('Pay_Period')
    @classmethod
    def pay_period(cls,v):
        if v > datetime.today():
            logger.error("Pay Period is not valid")
            raise ValueError("Pay Period is not valid")
        return v

    @field_validator('Base_Salary_Payroll')
    @classmethod
    def base_salary_payroll(cls,v):
        if v <=0:
            logger.error("Base Salary Payroll is less than or equal to 0")
            raise ValueError("Base Salary Payroll is less than or equal to 0")
        return v

    @field_validator('Basic_salary')
    @classmethod
    def basic_salary(cls,v):
        if v <0:
            logger.error("Basic Salary is less than 0")
            raise ValueError("Basic Salary is less than 0")
        return v

    @field_validator('HRA')
    @classmethod
    def hra(cls,v):
        if v <0:
            logger.error("HRA is less than 0")
            raise ValueError("HRA is less than 0")
        return v

    @field_validator('DA')
    @classmethod
    def da(cls,v):
        if v <0:
            logger.error("DA is less than 0")
            raise ValueError("DA is less than 0")
        return v

    @field_validator('Transport_Allowance')
    @classmethod
    def transport_allowance(cls,v):
        if v is not None and v <0:
            logger.error("Transport Allowance is less than 0")
            raise ValueError("Transport Allowance is less than 0")
        return v

    @field_validator('Medical_Allowance')
    @classmethod
    def medical_allowance(cls,v):
        if v <0:
            logger.error("Medical Allowance is less than 0")
            raise ValueError("Medical Allowance is less than 0")
        return v

    @field_validator('Special_Allowance')
    @classmethod
    def special_allowance(cls,v):
        if v <0:
            logger.error("Special Allowance is less than 0")
            raise ValueError("Special Allowance is less than 0")
        return v

    @field_validator('Overtime')
    @classmethod
    def overtime(cls,v):
        if v <0:
            logger.error("Overtime is less than 0")
            raise ValueError("Overtime is less than 0")
        return v

    @field_validator('Gross_Pay')
    @classmethod
    def gross_pay(cls,v):
        if v <0:
            logger.error("Gross Pay is less than 0")
            raise ValueError("Gross Pay is less than 0")
        return v

    @field_validator('PF_deduction')
    @classmethod
    def pf_deduction(cls,v):
        if v <0:
            logger.error("PF Deduction is less than 0")
            raise ValueError("PF Deduction is less than 0")
        return v

    @field_validator('ESI_deduction')
    @classmethod
    def esi_deduction(cls,v):
        if v <0:
            logger.error("ESI Deduction is less than 0")
            raise ValueError("ESI Deduction is less than 0")
        return v

    @field_validator('TDS_deduction')
    @classmethod
    def tds_deduction(cls,v):
        if v <0:
            logger.error("TDS Deduction is less than 0")
            raise ValueError("TDS Deduction is less than 0")
        return v

    @field_validator('PT_deduction')
    @classmethod
    def pt_deduction(cls,v):
        if v <0:
            logger.error("PT Deduction is less than 0")
            raise ValueError("PT Deduction is less than 0")
        return v

    @field_validator('Loan_deduction')
    @classmethod
    def loan_deduction(cls,v):
        if v <0:
            logger.error("Loan Deduction is less than 0")
            raise ValueError("Loan Deduction is less than 0")
        return v

    @field_validator('Total_deductions')
    @classmethod
    def total_deductions(cls,v):
        if v <0:
            logger.error("Total Deductions is less than 0")
            raise ValueError("Total Deductions is less than 0")
        return v

    @field_validator('Net_pay')
    @classmethod
    def net_pay(cls,v):
        if v <0:
            logger.error("Net Pay is less than 0")
            raise ValueError("Net Pay is less than 0")
        return v

    @field_validator('Payment_Mode')
    @classmethod
    def payment_mode(cls,v):
        if not v or not str(v).strip():
            logger.error("Payment Mode is not valid")
            raise ValueError("Payment Mode is not valid")
        return v

    @field_validator('Payment_Status')
    @classmethod
    def payment_status(cls,v):
        if not v or not str(v).strip():
            logger.error("Payment Status is not valid")
            raise ValueError("Payment Status is not valid")
        return v

    @field_validator('Payroll_Run_ID')
    @classmethod
    def payroll_run_id(cls,v):
        if not v or not str(v).strip():
            logger.error("Payroll Run ID is not valid")
            raise ValueError("Payroll Run ID is not valid")
        return v
