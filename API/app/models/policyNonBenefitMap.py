from __future__ import annotations
from sqlalchemy import Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class PolicyNonBenefitMap(Base):
    __tablename__ = "policy_non_benefit_map"
    __table_args__ = (
        PrimaryKeyConstraint("policy_id", "non_benefit_item_id", name="pk_policy_non_benefit_map"),
    )

    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policy.id", ondelete="CASCADE"), nullable=False)
    non_benefit_item_id: Mapped[int] = mapped_column(ForeignKey("non_benefit_items.id", ondelete="CASCADE"), nullable=False)

    policy: Mapped["InsurancePolicy"] = relationship(back_populates="non_benefit_links")
    non_benefit_item: Mapped["NonBenefitItem"] = relationship(back_populates="policies")
