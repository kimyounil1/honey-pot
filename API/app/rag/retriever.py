# app/rag/retriever.py
from __future__ import annotations
from typing import Sequence, List, Dict, Any
from app.services.common import Mode

"""
RAG 검색/컨텍스트 생성 모듈
- stage.rag_retrieve()에서 호출
- 현재는 안전한 스텁 동작(실서비스 연결 전에도 오류 없이 동작)
- 실제 연결 시:
  1) attachment_ids → 스토리지에서 파일 로드 → OCR → 텍스트 정리
  2) (옵션) 보험사/상품/버전/ICD 메타 기반 벡터검색 → 스니펫 압축
  3) 아래 포맷으로 문자열 블록 반환

[RAG]
- (제목) 핵심문장1. (p.12/제3장-5조)
- (제목) 핵심문장2. (p.13/제3장-6조)
🔎 출처: 현대해상 ○○실손(2024-01-01)
"""

async def retrieve(
    mode: Mode,
    user_id: str,
    query: str,
    attachment_ids: Sequence[str] | None,
    k: int = 6,
) -> str:
    """
    1) user_id 소유의 attachment_ids 텍스트 병합
    2) (옵션) 모드/쿼리/메타 기반 벡터 검색 스니펫 추가
    -> 합친 컨텍스트를 문자열로 리턴
    """
    # --- TODO: 실제 구현부 (스토리지/VectorDB 연결) ---
    # 예시 로직 스켈레톤:
    # texts: List[str] = []
    # for aid in (attachment_ids or []):
    #     file = await storage.get_file(user_id=user_id, attachment_id=aid)
    #     txt  = await ocr.ocr_file(file)  # 또는 서버 내 OCR 파이프라인
    #     if txt:
    #         texts.append(f"[첨부:{aid}]\n{txt[:4000]}")
    # snippets = await vectordb.search(query=query, k=k, meta={...})
    # rag_lines = [f"- {s['title']} {s['summary']} ({s['page_ref']}/{s['clause_id']})" for s in snippets]
    # src_line  = _format_sources(snippets)
    # block = ""
    # if rag_lines:
    #     block += "[RAG]\n" + "\n".join(rag_lines)
    #     if src_line:
    #         block += f"\n🔎 출처: {src_line}"
    # if texts:
    #     block = (block + "\n\n" if block else "") + "\n\n".join(texts)
    # return block

    # 안전한 기본값(연결 전): 빈 문자열 반환
    return ""

# --- (선택) 헬퍼 함수들: 실제 연결 시 활성화 ---
# def _format_sources(snippets: List[Dict[str, Any]]) -> str:
#     labels = []
#     for s in snippets:
#         lab = s.get("source_label")
#         if lab and lab not in labels:
#             labels.append(lab)
#     return " / ".join(labels)
