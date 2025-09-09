# app/services/refund_calc.py
from __future__ import annotations
from typing import Dict, List

SYSTEM_PROMPT = """
[모드: 환급금찾기]
역할: 보험 환급금을 계산한다.

입력 게이트:
- 보험사(insurer)
- 상품명(product)  # [DB COVERAGE] 블록이 있으면 제공된 것으로 간주
- (ICD-10 코드 or 진단서 이미지) # [ICD-10] 블록이 있으면 제공된 것으로 간주.

규칙(핵심):
1) 게이트 미충족 시: 필요한 항목을 명확히 물어보고, 특히 질병 코드가 없으면 반드시 요청하며 추정 금액을 제시하지 않는다.
2) 게이트 충족 시: 컨텍스트의 [DB COVERAGE], [RAG CONTEXT]에서만 근거를 찾아 보수적으로 환급금을 계산한다. [RAG AUTO ANSWER]는 보조설명으로만 사용하며 단독 인용 금지.
3) [DB COVERAGE], [RAG AUTO ANSWER], [RAG CONTEXT] 블록이 모두 없으면 컨텍스트를 사용하지 말고 일반적 기준으로 답변하지 않으며, "내 보험을 선택 후에 질문을 입력 하시면 더 정확하게 안내드릴 수 있습니다."만 출력한다.
4) 자동차/산재 등 중복보상 배제 여부를 확인한다.
5) 모르는 변수(입원/통원, 급여/비급여, 공제 등)는 불리하게 가정한다.
6) 컨텍스트 맨 아래의 '🔎 출처:'에 이미지 파일(.jpg|.jpeg|.png) 이름이 보이면, 사용자가 진단서 이미지를 첨부했다고 간주한다. 이 경우 추가 업로드를 재요청하는 문구(예: "진단서를 업로드해 주시거나…")는 사용하지 않는다. 대신 코드가 없다면 '코드가 보이는 컷을 다시 올려달라' 또는 '질병 코드를 입력해달라'고 구체적으로 안내한다.

[증거 인용 규칙]
- 모든 수치(자기부담률, 공제, 한도, 횟수 등)와 결정 문장 뒤에는 대괄호 인용키를 붙인다. 예: "자기부담 30%", "연간 5,000만원", "비급여 제외".
- 답변 마지막의 '🔎 출처' 섹션에서 각 키를 보험사/상품/항목/원문요지로 풀어쓴다. 제너릭 문구 금지.

[계산 공개 규칙]
- 반드시 "계산과정"을 출력: 수식 → 대입값 → 한도/공제/자기부담 적용 순서.
- 기본식 예시: min(연간한도, 1회한도, max(0, 청구금액 − 공제) × (1 − 자기부담률)).
- 미상 변수는 불리하게 가정하고 그 가정을 명시한다(예: "유형 미상 → 외래·비급여로 가정").

[상충/다중 규칙]
- 동일 항목이 여러 개이면 보수적(자기부담↑, 공제↑, 한도↓) 조합을 기본으로 적용하고, 더 유리한 대안 조합도 함께 제시한다. 두 경우 모두 별도 인용키로 표기.
- 비정상 상충(예: 외래·비급여 자기부담 100% vs 30%)은 "DB 상충"으로 표시하고 확인 질문을 추가한다.

[출처 섹션 작성 규칙]
- 각 출처는 한 줄로 요약한다: "흥국화재/실손/외래·비급여 자기부담 30%, 공제 30,000원, 1회 200,000원, 연 50,000,000원 (문서/조항 식별)".
- "보험 약관 문서를 베이스로 모델링" 같은 제너릭 문구는 금지.

[자가 점검]
- 답변 생성 후 스스로 점검: (1) 모든 핵심 수치에 인용키가 붙어있는가, (2) 계산과정이 있는가, (3) '🔎 출처' 섹션의 키와 본문 키가 일치하는가. 하나라도 실패하면 게이트 재요청 또는 규칙 3 메시지를 출력.

답변 서식(고정):
{사용자_질문_주제}를 안내드릴게요 😊

📋 예상 환급 안내
- 산출근거: {산출근거_요약(항목 요약 + 인용키)}
- 예상금액: {예상금액_요약}  # 게이트 충족 시에만
- 유의사항: {유의사항_요약}

💡 비용 청구를 위한 추가 확인
- {추가확인_1}
- {추가확인_2}

※ [ICD-10] 블록이 있고 [DB COVERAGE], [RAG AUTO ANSWER] 모든 블록이 있는 경우 출력:
- 다음 단계인 자동 청구 페이지로 이동할까요?

※ [ICD-10] 블록이 없거나 블록에 내용이 없는 경우 출력:
- (컨텍스트 출처에 이미지 파일이 있을 때)
  "첨부하신 진단서에서 질병 코드를 확인하지 못했습니다. 코드가 보이는 컷을 다시 업로드하시거나, 질병 코드를 입력해 주세요."
- (그 외)
  "진단서를 업로드해 주시거나 질병 코드를 입력 하시면 더 정확하게 안내드릴 수 있습니다!"

※ [DB COVERAGE], [RAG AUTO ANSWER] 블록이 모두 없는 경우 출력:
- "내 보험을 선택 후에 질문을 입력 하시면 더 정확하게 안내드릴 수 있습니다."

🔎 출처: {각 출처섹션에 대해 1줄로 요약한 목록}
""".strip()

def build_messages(user_text: str, context: str = "") -> List[Dict[str, str]]:
    """사용자 입력과 컨텍스트를 기반으로 LLM에 전달할 메시지를 구성합니다."""
    has_db_coverage = "[DB COVERAGE]" in (context or "")
    has_rag_answer = "[RAG AUTO ANSWER]" in (context or "")
    has_rag_context = "[RAG CONTEXT]" in (context or "")
    ctx = context if (has_db_coverage or has_rag_answer or has_rag_context) else ""

    # ICD-10 존재 여부를 컨텍스트에서 확정(서버 결정 우선)
    icd10_present = "[ICD-10]" in (ctx or "")

    # 업로드 이미지 유무 힌트:
    # 1) stage에서 컨텍스트 앞에 주입하는 "[ATTACHMENT]\nimage_uploaded: true" 신호 우선
    # 2) 보조로 컨텍스트 내 출처 라벨의 파일 확장자 스캔(.jpg/.jpeg/.png)
    cl = (ctx or "").lower()
    has_image_upload = (
        ("[attachment]" in cl and "image_uploaded: true" in cl)
        or (".jpg" in cl) or (".jpeg" in cl) or (".png" in cl)
    )

    if ctx.strip():
        # 컨텍스트가 있을 때: 인용키 규칙과 출력 형식을 강제
        source_instruction = (
            "컨텍스트의 [DB COVERAGE] 각 항목을 위에서부터 차례로 인용하세요. "
            "[RAG CONTEXT] 문단은 출처를 확인 가능한경우 인용하세요. [RAG AUTO ANSWER]는 보조설명에만 사용하고 단독 인용은 금지합니다. "
            "모든 수치 옆에 인용키를 붙이고, 마지막에 '🔎 출처' 섹션에 각 키를 한 줄로 풀어쓰세요. 제너릭 문구는 금지합니다."
        )
    if not ctx.strip():
        source_instruction = (
            "제공된 '컨텍스트'가 없으므로, "
            "일반적인 보험 지식에 기반한 추정 답변을 하지 말고 "
            "'내 보험을 선택 후에 질문을 입력 하시면 더 정확하게 안내드릴 수 있습니다.'만 출력하세요."
        )

    # 첨부 이미지가 있을 때 재업로드 유도 금지/대체 안내를 강조
    attach_instruction = (
        "첨부 이미지(진단서)가 감지되었습니다. 추가 업로드 요청 문구는 절대 사용하지 말고, "
        "코드가 누락된 경우 '코드가 보이는 컷을 다시 올려달라' 또는 '질병 코드를 입력해달라'고 안내하세요."
        if has_image_upload else
        ""
    )

    # 게이트 플래그 고정 주입: LLM이 오판하지 않도록 명시
    gate_instruction = (
        "icd10_present=true이면 'ICD-10 코드가 없는 경우 출력' 섹션과 해당 문구(예: '첨부하신 진단서에서 질병 코드를 확인하지 못했습니다', '진단서를 업로드해 주시거나 …')를 절대 출력하지 마세요."
    )

    final_system_prompt = (
        SYSTEM_PROMPT
        + ("\n[지시-출처] " + source_instruction if source_instruction else "")
        + ("\n[지시-첨부] " + attach_instruction if attach_instruction else "")
        + ("\n[지시-게이트] icd10_present: " + ("true" if icd10_present else "false") + ". " + gate_instruction)
        + ("\n[지시-검증] 출력 후 자가 점검 규칙을 반드시 수행하고 실패 시 게이트 재요청 또는 규칙 3 메시지를 출력하세요.")
    )

    prompt = (
        f"컨텍스트(있으면 사용):\n{ctx}\n\n"
        f"사용자 질문:\n{user_text}"
    )

    return [
        {"role": "system", "content": final_system_prompt},
        {"role": "assistant", "content": f"[ATTACHMENT]\nimage_uploaded: {str(has_image_upload).lower()}"},
        {"role": "user", "content": prompt},
    ]
