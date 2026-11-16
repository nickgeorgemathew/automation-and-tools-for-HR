"""
Schema_validator.py
-------------------
Row-level contracts for the three feeds. Field names match the CSV headers exactly
(including case), and field ORDER matches the warehouse tables.

A row is rejected only for MALFORMED data (bad ID, unknown department, impossible
date, negative money). Business discrepancies (wrong salary, wrong GL amount) are
NOT rejected here: they must reach the reconciliation engine so they get flagged.
"""
import logging
import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from config import settings

logger = logging.getLogger("pipeline")

EMP_ID = re.compile(r"^E\d{4,}$")                 # E0001, E9901
MASKED_ACCOUNT = re.compile(r"^[Xx*\d]{4,20}$")   # masked (XXXX2679) or plain digits are both valid


def _check_employee_id(v: str) -> str:
    if not isinstance(v, str) or not EMP_ID.match(v):
        raise ValueError(f"Employee_ID must look like E0001, got {v!r}")
    return v


def _check_in(v: str, allowed: list, label: str) -> str:
    if v not in allowed:
        raise ValueError(f"{label} {v!r} is not an allowed value")
    return v


def _not_future(v: date, label: str) -> date:
    if v > date.today():
        raise ValueError(f"{label} {v} is in the future")
    return v


class HRISRecord(BaseModel):
    Employee_ID: str
    Employee_Name: str = Field(min_length=1)
    Department: str
    Designation: str
    Category: str
    Date_Of_Joining: date
    Date_Of_Leaving: Optional[date] = None
    Employment_Status: str
    Base_Salary_HRIS: float = Field(ge=0)
    Bank_Name: str = Field(min_length=1)
    Bank_Account: str
    UAN_Number: str
    PAN_Number: str
    Location: str

    _emp = field_validator("Employee_ID")(lambda cls, v: _check_employee_id(v))
    _dept = field_validator("Department")(lambda cls, v: _check_in(v, settings.department, "Department"))
    _desig = field_validator("Designation")(lambda cls, v: _check_in(v, settings.designation, "Designation"))
    _cat = field_validator("Category")(lambda cls, v: _check_in(v, settings.category, "Category"))
    _status = field_validator("Employment_Status")(
        lambda cls, v: _check_in(v, settings.Allowed_Employment_Status, "Employment_Status"))
    _loc = field_validator("Location")(lambda cls, v: _check_in(v, settings.location, "Location"))
    _doj = field_validator("Date_Of_Joining")(lambda cls, v: _not_future(v, "Date_Of_Joining"))

    @field_validator("Bank_Account")
    @classmethod
    def bank_account(cls, v):
        # masked accounts such as XXXX2679 are VALID (they are how the HRIS exports them)
        if not MASKED_ACCOUNT.match(v):
            raise ValueError("Bank_Account must be digits and/or X-masked")
        return v

    @field_validator("UAN_Number")
    @classmethod
    def uan(cls, v):
        if len(v) != 12:
            raise ValueError(f"UAN_Number must be 12 characters, got {len(v)}")
        return v

    @field_validator("PAN_Number")
    @classmethod
    def pan(cls, v):
        if len(v) != 10:
            raise ValueError(f"PAN_Number must be 10 characters, got {len(v)}")
        return v

    @model_validator(mode="after")
    def cross_field_rules(self):
        if self.Date_Of_Leaving and self.Date_Of_Leaving < self.Date_Of_Joining:
            raise ValueError("Date_Of_Leaving is before Date_Of_Joining")
        # v2: a zero salary is only acceptable for someone who has left
        if self.Base_Salary_HRIS == 0 and self.Employment_Status != "Terminated":
            raise ValueError("Base_Salary_HRIS is 0 for a non-terminated employee")
        return self


class PayrollRegister(BaseModel):
    Employee_ID: str
    Employee_Name: str = Field(min_length=1)
    Department: str
    Pay_Period: date
    Base_Salary_Payroll: float = Field(ge=0)
    Basic_Salary: float = Field(ge=0)
    HRA: float = Field(ge=0)
    DA: float = Field(ge=0)
    Transport_Allowance: Optional[float] = Field(default=None, ge=0)
    Medical_Allowance: float = Field(ge=0)
    Special_Allowance: float = Field(ge=0)
    Overtime: float = Field(ge=0)
    Gross_Pay: float = Field(ge=0)
    PF_Deduction: float = Field(ge=0)
    ESI_Deduction: float = Field(ge=0)
    TDS_Deduction: float = Field(ge=0)
    PT_Deduction: float = Field(ge=0)
    Loan_Deduction: float = Field(ge=0)
    Total_Deductions: float = Field(ge=0)
    Net_Pay: float = Field(ge=0)
    Payment_Mode: str = Field(min_length=1)
    Payment_Status: str = Field(min_length=1)
    Payroll_Run_ID: str = Field(min_length=1)
    Remarks: Optional[str] = None

    _emp = field_validator("Employee_ID")(lambda cls, v: _check_employee_id(v))
    _dept = field_validator("Department")(lambda cls, v: _check_in(v, settings.department, "Department"))
    _period = field_validator("Pay_Period")(lambda cls, v: _not_future(v, "Pay_Period"))

    @model_validator(mode="after")
    def base_salary_rule(self):
        # Manual adjustment rows legitimately carry a base salary of 0
        if self.Base_Salary_Payroll <= 0 and self.Payment_Mode != "Manual_Adjustment":
            raise ValueError("Base_Salary_Payroll must be > 0 unless Payment_Mode is Manual_Adjustment")
        return self


class FinanceLedger(BaseModel):
    GL_Entry_ID: str = Field(min_length=1)
    Employee_ID: str
    Department: str
    Pay_Period: date
    GL_Account_Code: str = Field(min_length=1)
    GL_Amount_Posted: float = Field(ge=0)
    Payroll_Net_Pay_Reference: float = Field(ge=0)
    Posting_Date: date
    Posted_By: str = Field(min_length=1)
    GL_Remarks: Optional[str] = None

    _emp = field_validator("Employee_ID")(lambda cls, v: _check_employee_id(v))
    _dept = field_validator("Department")(lambda cls, v: _check_in(v, settings.department, "Department"))
    _period = field_validator("Pay_Period")(lambda cls, v: _not_future(v, "Pay_Period"))
    _posted = field_validator("Posting_Date")(lambda cls, v: _not_future(v, "Posting_Date"))

    @field_validator("GL_Account_Code", "Posted_By")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("must not be blank")
        return v


SCHEMA_MAP = {
    "hris_export": HRISRecord,
    "payroll_register": PayrollRegister,
    "gl_dump": FinanceLedger,
}

__all__ = ["HRISRecord", "PayrollRegister", "FinanceLedger", "SCHEMA_MAP", "datetime"]