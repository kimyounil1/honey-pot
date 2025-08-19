from sqlalchemy import Index, UniqueConstraint
from . import Column, Integer, String, Text, Base  # 기존 models/__init__.py 스타일 유지

class NonBenefitItem(Base):
    __tablename__ = "non_benefit_items"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    seq_no = Column(String(50), nullable=True)
    code = Column(String(50), nullable=True)
    category_mid = Column(Text, nullable=True)
    category_small = Column(Text, nullable=True)
    category_detail = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    extra_1 = Column(Text, nullable=True)
    extra_2 = Column(Text, nullable=True)
    extra_3 = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("code", name="uq_non_benefit_code"),
        Index("idx_non_benefit_code", "code"),
    )