# app/schemas/policySchema.py
from . import BaseModel, date, Optional

class InsurancePolicyBase(BaseModel):
    policy_id: Optional[str]       # OS와 동기화되는 외부 id (문자)
    insurer: Optional[str]
    product_code: Optional[str]
    version: Optional[str]
    effective_date: Optional[date]
    policy_type: Optional[str]
    coverage_summary: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    coverage_item_names: list[str] = []

class InsurancePolicyCreate(InsurancePolicyBase):
    user_id: int

class InsurancePolicyRead(InsurancePolicyBase):
    id: int
    user_id: int
    class Config:
        orm_mode = True

class InsurancePolicyInsurers(BaseModel):
    insurers: list[str]

class InsurancePolicyList(BaseModel):
    insurer: str
    policies: list[str]

class PolicyList(BaseModel):
    policies: list[InsurancePolicyRead]