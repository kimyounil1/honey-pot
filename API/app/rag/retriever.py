# app/rag/retriever.py
from typing import Sequence
from app.services.common import Mode

async def retrieve(
    mode: Mode,
    user_id: str,
    query: str,
    attachment_ids: Sequence[str] | None,
    k: int = 6,
) -> str:
    """
    1) user_id 소유의 attachment_ids 텍스트 병합
    2) (옵션) 모드별 벡터 인덱스에서 query 검색 결과 추가
    -> 합친 컨텍스트를 문자열로 리턴
    """
    # TODO: DB 조회 + OCR/PDF 파싱 텍스트 합치기 (현재는 스텁)
    return ""
