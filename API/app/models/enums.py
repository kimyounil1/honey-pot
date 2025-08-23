# app/models/enums.py
import enum
from sqlalchemy.dialects.postgresql import ENUM

class ProductType(str, enum.Enum):
    암보험 = "암보험"; 실손 = "실손"; 운전자 = "운전자"; 종신 = "종신"
    정기 = "정기"; 치아 = "치아"; 어린이 = "어린이"; 간병 = "간병"; 기타 = "기타"

class RenewalType(str, enum.Enum):
    비갱신 = "비갱신"; 연만기갱신 = "연만기갱신"; _3년갱신 = "3년갱신"; _5년갱신 = "5년갱신"; 기타 = "기타"

# 마이그레이션 전제였다면 create_type=False 였을 텐데, 옵션 A에서는 그대로 둬도 됨
product_type_enum = ENUM(ProductType, name="product_type_enum", create_type=False)
renewal_type_enum = ENUM(RenewalType, name="renewal_type_enum", create_type=False)
