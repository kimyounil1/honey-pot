# app/services/non_benefit_import.py
import pandas as pd

# 원본 엑셀 헤더 → 영문 필드 매핑
COL_MAP = {
    "연번": "seq_no",
    "코드": "code",
    "중분류": "category_mid",
    "소분류": "category_small",
    "상세분류": "category_detail",
    "비 고": "note"
}

def read_excel_to_records(file_bytes: bytes) -> list[dict]:
    df = pd.read_excel(file_bytes, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    # 누락된 컬럼이 있어도 전부 보장
    for k in COL_MAP.keys():
        if k not in df.columns:
            df[k] = None
    df = df[list(COL_MAP.keys())]

    # 완전 공행 제거
    df = df.dropna(how="all")

    # 공백/NaN 정리
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace({"None": None, "nan": None, "NaN": None, "": None})

    df = df.rename(columns=COL_MAP)
    return df.to_dict(orient="records")
