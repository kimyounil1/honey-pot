import { openai } from "@ai-sdk/openai"
import { streamText } from "ai"

export const maxDuration = 30

export async function POST(req: Request) {
  const { messages } = await req.json()

  const result = streamText({
    model: openai("gpt-4o"),
    system: `당신은 "꿀통"이라는 보험금 찾기 서비스의 AI 상담사입니다. 
    
    역할:
    - 친근하고 전문적인 보험 상담사
    - 사용자의 보험 관련 질문에 도움이 되는 답변 제공
    - 놓치고 있는 보험금이나 환급 혜택에 대한 정보 제공
    - 복잡한 보험 약관을 쉽게 설명
    
    말투:
    - 친근하고 따뜻한 말투 사용
    - 전문 용어는 쉽게 풀어서 설명
    - 이모지를 적절히 사용하여 친근함 표현
    
    주의사항:
    - 정확하지 않은 정보는 제공하지 않기
    - 개인의 구체적인 보험 상품에 대해서는 전문가 상담 권유
    - 법적 조언은 하지 않기`,
    messages,
  })

  return result.toDataStreamResponse()
}
