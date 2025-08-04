# 임시 스키마 파일

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

### -----------------
### USER
### -----------------
class UserBase(BaseModel):
    name: str
    email: str
    birth_date: Optional[date] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    user_id: int
    class Config:
        orm_mode = True


### -----------------
### INSURANCE_POLICY
### -----------------
class InsurancePolicyBase(BaseModel):
    insurance_company: Optional[str]
    policy_type: Optional[str]
    coverage_summary: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

class InsurancePolicyCreate(InsurancePolicyBase):
    user_id: int

class InsurancePolicyRead(InsurancePolicyBase):
    policy_id: int
    user_id: int
    class Config:
        orm_mode = True


### -----------------
### CLAIM
### -----------------
class ClaimBase(BaseModel):
    claim_date: Optional[date]
    claimed_amount: Optional[float]
    approved_amount: Optional[float]
    status: Optional[str]

class ClaimCreate(ClaimBase):
    user_id: int
    policy_id: int

class ClaimRead(ClaimBase):
    claim_id: int
    user_id: int
    policy_id: int
    class Config:
        orm_mode = True
