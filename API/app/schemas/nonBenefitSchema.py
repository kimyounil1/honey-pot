from . import BaseModel, Optional  # 레포의 __init__.py 스타일과 맞춤

class NonBenefitItemRead(BaseModel):
    id: int
    seq_no: Optional[str] = None
    code: Optional[str] = None
    category_mid: Optional[str] = None
    category_small: Optional[str] = None
    category_detail: Optional[str] = None
    note: Optional[str] = None
    extra_1: Optional[str] = None
    extra_2: Optional[str] = None
    extra_3: Optional[str] = None

    class Config:
        orm_mode = True