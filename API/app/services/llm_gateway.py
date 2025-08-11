
import os
from typing import Dict, Any, List
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 모드별 모델/샘플 파라미터를 다르게 쓰고 싶으면 여기서 조절
DEFAULT_MODEL = "gpt-4o-mini"

async def call_llm(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    """
    3단계: LLM 호출 전용. 입력은 2단계에서 만든 messages 그대로.
    """
    resp = await client.responses.create(model=model, input=messages)
    # 최신 SDK는 output_text 제공(툴 호출 등 특수 경우엔 대비)
    return getattr(resp, "output_text", str(resp))
