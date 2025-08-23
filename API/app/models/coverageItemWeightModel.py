from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, String, Boolean, Numeric, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .enums import product_type_enum

class CoverageItemWeight(Base):
    __tablename__ = "coverage_item_weight"
    __table_args__ = (
        PrimaryKeyConstraint("product_type", "coverage_item_id", name="pk_coverage_item_weight"),
    )

    product_type: Mapped[str] = mapped_column(product_type_enum, nullable=False)
    coverage_item_id: Mapped[int] = mapped_column(ForeignKey("coverage_item.id", ondelete="CASCADE"), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)  # 0~1
    is_core: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(String)

    # (선택) 역참조가 필요하면 CoverageItem 쪽에 relationship 추가 가능
