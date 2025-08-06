from . import BaseModel, date, Optional

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