# app/services/extractor.py
import re
from datetime import date, datetime
from typing import Optional, Tuple

# -----------------------------
# 날짜 파싱용 패턴 (기존 유지)
# -----------------------------
DATE_PATTERNS = [
    r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",          # 2025-08-24, 2025.08.24, 2025/08/24
    r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일",  # 2025년 8월 24일
]

def _safe_add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 2/29 -> 2/28 보정
        return d.replace(month=2, day=28, year=d.year + years)

def parse_first_date(text: str) -> Optional[date]:
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            y, mth, d = map(int, m.groups())
            return date(y, mth, d)
    return None

# ------------------------------------------------------------------
# 금액 파서 강화를 위한 전처리/정규식
#  - ICD-10 코드(S83.5 등), 날짜, policy_id, 퍼센트 등을 제거
#  - '만원/천원/원' 단위 및 왼쪽 문맥(환급/보험/청구/금액/지급) 이용
#  - '8만 5천원', '12만원' 같은 한글 금액도 처리
# ------------------------------------------------------------------
ICD10_RE = re.compile(r"\b[A-TV-Z][0-9]{2}(?:\.[0-9])?\b")   # U코드 제외
DATE_RE_INLINE = re.compile(r"(?:" + "|".join(DATE_PATTERNS) + r")")
POLICY_ID_RE = re.compile(r"(?:policy_id|상품코드|상품ID)\s*[:：]?\s*[A-Za-z0-9\-_]+")
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")

# 숫자 + (만원|천원|원/KRW/won) 패턴
AMOUNT_RE = re.compile(
    r"(?:(?:예상|추정|환급|보험|청구|지급)?\s*(?:금|금액|환급금|보험금|청구액)\s*[:\-]?\s*)?"
    r"((?:\d{1,3}(?:,\d{3})+)|\d+)\s*(만원|천원|원|KRW|원정|won)?",
    re.IGNORECASE,
)

# '8만 5천원', '8만5천원', '12만원' 같은 한글 금액
KOREAN_AMOUNT_RE = re.compile(
    r"(?:(?:예상|추정|환급|보험|청구|지급)?\s*(?:금|금액|환급금|보험금|청구액)\s*[:\-]?\s*)?"
    r"(?:(\d+)\s*만\s*(\d+)?\s*천?\s*원?|(\d+)\s*만원)",
    re.IGNORECASE,
)

AMOUNT_LEFT_KEYWORDS = ("환급", "보험", "보험금", "청구", "금액", "지급")


def _strip_noise_for_amount(text: str) -> str:
    """금액 추출에 방해되는 숫자성 토큰 제거."""
    t = ICD10_RE.sub(" ", text)           # S83.5 등 제거
    t = DATE_RE_INLINE.sub(" ", t)        # 날짜 제거
    t = POLICY_ID_RE.sub(" ", t)          # policy_id: KOR-HEALTH-001 제거
    t = PERCENT_RE.sub(" ", t)            # 20% 같은 퍼센트 제거
    return t


def _parse_korean_amounts(text: str) -> list[int]:
    """'8만 5천원', '12만원' 등 한글 금액을 정수 원으로 리스트화."""
    values: list[int] = []
    for m in KOREAN_AMOUNT_RE.finditer(text):
        # 그룹1: (\d+)만 [(\d+)천]원   | 그룹3: (\d+)만원
        if m.group(1):
            man = int(m.group(1))
            cheon = int(m.group(2)) if m.group(2) else 0
            values.append(man * 10_000 + cheon * 1_000)
        elif m.group(3):
            values.append(int(m.group(3)) * 10_000)
    return values


def parse_expected_amount(text: str) -> Optional[float]:
    """
    금액을 원 단위 float로 반환.
    - 숫자/단위 혼재 문장에서 가장 그럴듯한(보통 가장 큰) 값을 선택
    - 날짜/ICD/policy_id/퍼센트 숫자는 제외
    """
    if not text:
        return None

    clean = _strip_noise_for_amount(text)

    candidates: list[int] = []

    # 1) 한글 금액 ('8만 5천원', '12만원')
    candidates.extend(_parse_korean_amounts(clean))

    # 2) 숫자 + 단위 / 혹은 왼쪽 문맥 키워드가 있는 숫자
    for m in AMOUNT_RE.finditer(clean):
        num_s, unit = m.group(1), (m.group(2) or "").lower()
        left_ctx = clean[max(0, m.start() - 25): m.start()]  # 왼쪽 25자 문맥

        # 단위가 전혀 없고 왼쪽 문맥에도 키워드가 없으면 잡음으로 간주 (예: '83' 등)
        if not unit and not any(k in left_ctx for k in AMOUNT_LEFT_KEYWORDS):
            continue

        try:
            n = int(num_s.replace(",", "").replace(" ", ""))
        except ValueError:
            continue

        if unit in ("만원",):
            n *= 10_000
        elif unit in ("천원",):
            n *= 1_000
        # (원 / KRW / won / 원정) 은 그대로

        # 너무 비현실적으로 작은 값(예: 10원 미만)은 잡음으로 배제
        if n < 10:
            continue

        candidates.append(n)

    if not candidates:
        return None

    # 여러 개면 가장 큰 값을 반환 (일반적으로 원하는 금액일 확률이 높음)
    return float(max(candidates))


def looks_like_refund_answer(text: str) -> bool:
    # 매우 가벼운 휴리스틱(LLM 도입 전)
    keys = ["환급", "청구", "해지환급금", "만기환급금"]
    return any(k in text for k in keys)


def extract_core_info(
    chat_started_at: date,
    combined_text: str
) -> Tuple[date, Optional[str], Optional[str], Optional[str], Optional[float]]:
    """
    returns: (base_date, disease_name, disease_code, policy_id, expected_amount)
    """
    base = parse_first_date(combined_text) or chat_started_at

    # 질병/코드: 단순 라인 패턴
    m1 = re.search(r"(?:질병명|병명|진단명)\s*[:：]\s*([^\n]+)", combined_text)
    disease_name = m1.group(1).strip() if m1 else None

    m2 = re.search(r"(?:ICD-?10|진단코드)\s*[:：]\s*([A-Z]\d{2,3}(?:\.\d+)?)", combined_text, re.IGNORECASE)
    disease_code = m2.group(1).upper() if m2 else None

    m3 = re.search(r"(?:policy_id|상품코드|상품ID)\s*[:：]\s*([A-Za-z0-9\-_]+)", combined_text)
    policy_id = m3.group(1) if m3 else None

    amount = parse_expected_amount(combined_text)
    return base, disease_name, disease_code, policy_id, amount


def compute_deadline(base: date, years: int = 3) -> date:
    return _safe_add_years(base, years)
