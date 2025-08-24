from __future__ import annotations
from typing import Optional
from sqlalchemy import Numeric, String, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .enums import product_type_enum
from .base import Base
class ComplementarityRules(Base):
    __tablename__ = "complementarity_rules"
    __table_args__ = (
        PrimaryKeyConstraint("src_product_type", "dst_product_type", name="pk_complementarity_rules"),
    )

    src_product_type: Mapped[str] = mapped_column(product_type_enum, nullable=False)  # 보유 상품군
    dst_product_type: Mapped[str] = mapped_column(product_type_enum, nullable=False)  # 추천 상품군
    effect: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)  # -1 ~ +1
    notes: Mapped[Optional[str]] = mapped_column(String)
