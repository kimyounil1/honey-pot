# app/services/extractor.py
import re
from datetime import date
from typing import Optional, Tuple, List

# -----------------------------
# 날짜 파싱 패턴
# -----------------------------
DATE_PATTERNS = [
    r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",          # 2025-08-24, 2025.08.24, 2025/08/24
    r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일",  # 2025년 8월 24일
]

LABELS = r"(검사일|진단일|진단 날짜|사고일|사고 날짜|처치일|진료일|수술일)"
DATE_RE_INLINE = re.compile(r"(?:" + "|".join(DATE_PATTERNS) + r")")

# -----------------------------
# 금액 파싱을 방해하는 토큰(숫자)을 미리 제거
# -----------------------------
ICD10_RE = re.compile(r"\b[A-TV-Z][0-9]{2}(?:\.[0-9])?\b")   # U코드 제외
POLICY_ID_RE = re.compile(r"(?:policy_id|상품코드|상품ID)\s*[:：]?\s*[A-Za-z0-9\-_]+")
PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")

# 숫자 + (만원|천원|원/KRW/won) 패턴
AMOUNT_RE = re.compile(
    r"(?:(?:예상|추정|환급|보험|청구|지급)?\s*(?:금|금액|환급금|보험금|청구액)\s*[:\-]?\s*)?"
    r"((?:\d{1,3}(?:,\d{3})+)|\d+)\s*(만원|천원|원|KRW|원정|won)?",
    re.IGNORECASE,
)

# '8만 5천원', '12만원' 같은 한글 금액
KOREAN_AMOUNT_RE = re.compile(
    r"(?:(?:예상|추정|환급|보험|청구|지급)?\s*(?:금|금액|환급금|보험금|청구액)\s*[:\-]?\s*)?"
    r"(?:(\d+)\s*만\s*(\d+)?\s*천?\s*원?|(\d+)\s*만원)",
    re.IGNORECASE,
)

AMOUNT_LEFT_KEYWORDS = ("환급", "보험", "보험금", "청구", "금액", "지급")


# -----------------------------
# 날짜 유틸
# -----------------------------
def _to_date(y: int, m: int, d: int) -> date:
    return date(int(y), int(m), int(d))

def _safe_add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 2/29 -> 2/28 보정
        return d.replace(month=2, day=28, year=d.year + years)

def _find_all_dates(s: str) -> List[date]:
    out: List[date] = []
    for y, m, d in re.findall(DATE_PATTERNS[0], s):
        out.append(_to_date(int(y), int(m), int(d)))
    for y, m, d in re.findall(DATE_PATTERNS[1], s):
        out.append(_to_date(int(y), int(m), int(d)))
    return out

def parse_first_date(text: str) -> Optional[date]:
    # (하위 호환: 필요 시 사용)
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            y, mth, d = map(int, m.groups())
            return date(y, mth, d)
    return None

def _parse_labeled_date(text: str) -> Optional[date]:
    # 라벨이 붙은 날짜를 최우선으로 채택
    for pat in [
        rf"{LABELS}\s*[:：]?\s*{DATE_PATTERNS[0]}",  # label: YYYY-MM-DD
        rf"{LABELS}\s*[:：]?\s*{DATE_PATTERNS[1]}",  # label: YYYY년 M월 D일
    ]:
        m = re.search(pat, text)
        if m:
            # m.groups() = (label, y, m, d) 형태
            y, mm, dd = m.groups()[-3:]
            return _to_date(int(y), int(mm), int(dd))
    return None

def _choose_base_date(chat_started_at: date, text: str) -> date:
    """
    기산일(base_date) 선택 규칙:
      1) '검사일/진단일/사고일/…' 라벨이 붙은 날짜가 있으면 그걸 사용
      2) 문서 내 모든 날짜 중 '오늘보다 미래'는 제외하고 가장 이른 과거/오늘 날짜
      3) 없으면 채팅 시작일
    """
    today = date.today()

    labeled = _parse_labeled_date(text)
    if labeled:
        return labeled

    all_dates = _find_all_dates(text)
    past_or_today = [d for d in all_dates if d <= today]
    if past_or_today:
        return min(past_or_today)

    return chat_started_at


# -----------------------------
# 금액 파싱
# -----------------------------
def _strip_noise_for_amount(text: str) -> str:
    """금액 추출에 방해되는 숫자성 토큰 제거."""
    t = ICD10_RE.sub(" ", text)           # S83.5 등 제거
    t = DATE_RE_INLINE.sub(" ", t)        # 날짜 제거
    t = POLICY_ID_RE.sub(" ", t)          # policy_id: KOR-HEALTH-001 제거
    t = PERCENT_RE.sub(" ", t)            # 20% 같은 퍼센트 제거
    return t

def _parse_korean_amounts(text: str) -> List[int]:
    """'8만 5천원', '12만원' 등 한글 금액을 정수 원으로 리스트화."""
    values: List[int] = []
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
    - 날짜/ICD/policy_id/퍼센트 숫자는 제외
    - '만원/천원/원' 단위, '8만 5천원' 등 한글 금액 처리
    - 문맥상 금액일 가능성이 낮은(단위도 없고, 왼쪽에 키워드도 없는) 작은 숫자는 배제
    """
    if not text:
        return None

    clean = _strip_noise_for_amount(text)
    candidates: List[int] = []

    # 1) 한글 금액 ('8만 5천원', '12만원')
    candidates.extend(_parse_korean_amounts(clean))

    # 2) 숫자 + 단위 / 혹은 왼쪽 문맥 키워드가 있는 숫자
    for m in AMOUNT_RE.finditer(clean):
        num_s, unit = m.group(1), (m.group(2) or "").lower()
        left_ctx = clean[max(0, m.start() - 25): m.start()]  # 왼쪽 25자 문맥

        # 단위 없고, 왼쪽에도 금액 관련 키워드가 없으면 잡음으로 간주 (예: '83' 같은 날짜 파편)
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

        if n < 10:
            continue

        candidates.append(n)

    if not candidates:
        return None

    # 여러 개면 가장 그럴듯한(일반적으로 큰 값)을 채택
    return float(max(candidates))


# -----------------------------
# 외부 API
# -----------------------------
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
    base = _choose_base_date(chat_started_at, combined_text)

    # 질병/코드/상품코드 추출
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
