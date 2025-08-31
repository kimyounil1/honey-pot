// /app/api/chat/route.ts
import { cookies } from 'next/headers';

export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;
    if (!token) {
      return new Response('Unauthorized', { status: 401 });
    }

    // 1) 신규/레거시 모두 허용해서 파싱
    const body = await req.json();

    // 신규 스키마 우선: role/text/prev_chats/disease_code/product_id
    let role: string = body.role ?? 'user';
    let text: string | undefined = body.text;
    let prev_chats: string[] | undefined = body.prev_chats;
    let disease_code: string | null = body.disease_code ?? null;
    let product_id: string | null = body.product_id ?? null;

    // 2) 레거시(messages: [...])가 오면 자동 변환
    if ((!text || !prev_chats) && Array.isArray(body.messages)) {
      const messages = body.messages;
      const lastUserMessage = messages[messages.length - 1];
      if (!lastUserMessage || lastUserMessage.role !== 'user') {
        return new Response('Valid user message not found in the request body.', { status: 400 });
      }
      role = 'user';
      text = lastUserMessage.content;
      prev_chats = messages.map((m: any) => m.content);

      // 첨부 승격(레거시 경로 보완)
      disease_code = lastUserMessage?.attachment?.disease_code ?? disease_code;
      product_id   = lastUserMessage?.attachment?.product_id   ?? product_id;
    }

    if (!text) {
      return new Response('Field "text" is required.', { status: 400 });
    }

    // 3) FastAPI AskBody(JSON)로 전송
    const payload = {
      role,
      text,
      prev_chats,     // Optional[List[str]]
      // chat_id 없음(신규 채팅)
      disease_code,   // nullable
      product_id,     // nullable
    };

    const fastApiResponse = await fetch('http://API:8000/chat/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',   // ✅ JSON으로 변경
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      console.error('FastAPI backend returned an error:', errorBody);
      return new Response(errorBody, { status: fastApiResponse.status });
    }

    const responseBody = await fastApiResponse.json();
    return new Response(JSON.stringify(responseBody), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error in Next.js API route (/api/chat):', error);
    if (error instanceof Error) {
      return new Response(error.message, { status: 500 });
    }
    return new Response('An unknown error occurred.', { status: 500 });
  }
}
