from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Text, ForeignKey, Enum, PickleType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from app.database import Base
from .enums import ProductType, RenewalType
from . import userModel  # ensure User is registered before policy relationships
from .policyModel import InsurancePolicy
from .coverageModel import CoverageItem
from .policyCoverageModel import PolicyCoverage
from .nonBenefitModel import NonBenefitItem
from .policyPremiumModel import PolicyPremium
from .coverageItemWeightModel import CoverageItemWeight
from .complementarityRulesModel import ComplementarityRules
from . import userModel
from . import chatModel
from .assessmentModel import Assessment
from .attachmentModel import AssessmentAttachment
from .assessmentMessageModel import AssessmentMessage
__all__ = [
    "Base", "Column", "Integer", "String", "Date", "DateTime", "Float", "Text",
    "ForeignKey", "Enum", "PickleType", "relationship", "MutableList",
    "ProductType", "RenewalType",
    "InsurancePolicy",
    "CoverageItem",
    "PolicyCoverage",
    "NonBenefitItem",
    "PolicyPremium",
    "CoverageItemWeight",
    "ComplementarityRules",
    "Assessment",
    "AssessmentAttachment",
    "AssessmentMessage",
]
