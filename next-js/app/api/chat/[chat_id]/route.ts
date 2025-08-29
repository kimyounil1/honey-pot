import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

interface Params{
  params: { chat_id: number }
}

async function getAccessToken(){
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  return token
}

export async function GET(request: NextRequest, { params }: Params) { 
  try{
    const token = await getAccessToken()
    if (!token) {
      window.alert("승인되지 않은 접근입니다.")
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const { chat_id } = await params
    const fastApiResponse = await fetch(`http://API:8000/chat/${chat_id}/messages`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      console.error('FastAPI backend returned an error:', errorBody);
      return new NextResponse(errorBody, { status: fastApiResponse.status });
    }

    const responseBody = await fastApiResponse.json();

    return NextResponse.json(responseBody);

  } catch (error) {
    console.error('Error in Next.js API route (/api/chat/[chat_id]):', error);
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('An unknown error occurred.', { status: 500 });
  }
}

export async function POST(request: NextRequest, { params }: Params) {
  try {
    const token = await getAccessToken();
    const { chat_id } = await params;

    // 1) 클라이언트가 보내온 바디를 읽음(신규/레거시 모두 허용)
    const body = await request.json();

    // 신규 스키마 우선
    let role: string = body.role ?? 'user';
    let text: string | undefined = body.text;
    let prev_chats: string[] | undefined = body.prev_chats;
    let disease_code: string | null = body.disease_code ?? null;
    let product_id: string | null = body.product_id ?? null;

    // // 2) 레거시(body.messages: [...])가 들어오면 변환
    // if ((!text || !prev_chats) && Array.isArray(body.messages)) {
    //   const messages = body.messages;
    //   const lastUserMessage = messages[messages.length - 1];
    //   if (!lastUserMessage || lastUserMessage.role !== 'user') {
    //     return new Response('Valid user message not found in the request body.', { status: 400 });
    //   }
    //   role = 'user';
    //   text = lastUserMessage.content;
    //   prev_chats = messages.map((m: any) => m.content);

    //   // 첨부 승격(레거시 경로 보완)
    //   disease_code = lastUserMessage?.attachment?.disease_code ?? disease_code;
    //   product_id   = lastUserMessage?.attachment?.product_id   ?? product_id;
    // }

    // 최종 유효성
    if (!text) {
      return new Response('Field "text" is required.', { status: 400 });
    }

    // 3) FastAPI에 JSON으로 바로 전달 (AskBody: role, text, prev_chats, chat_id, disease_code, product_id)
    const payload = {
      role,
      text,
      prev_chats,          // Optional[List[str]]
      chat_id,             // params에서 옴
      disease_code,        // nullable
      product_id,          // nullable
    };

    const fastApiResponse = await fetch('http://API:8000/chat/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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