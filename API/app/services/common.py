from enum import Enum

class Mode(str, Enum):
    STARTEND = "startend"
    TERMS    = "terms_analysis"   # 약관분석
    REFUND   = "refund_calc"      # 환급금찾기
    RECO     = "recommend"        # 보험추천
    FALLBACK = "fallback"         # 예외질문(보험 외 주제는 거절 + 3기능 유도)

GREETING = "안녕하세요 꿀통입니다. 🐝 첫 대화를 진심으로 환영합니다!\n\n"

TERMS_KEYS  = ("약관","특약","증권","보장","면책","청구","지급조건","보장내역","보장범위")
REFUND_KEYS = ("환급","해지","만기","되돌려","돌려","납입환급","환급금","해지환급","만기환급")
RECO_KEYS   = ("추천","뭐 들어야","필요한 보험","권장","맞춤설계","가입권고","보장갭","설계")
