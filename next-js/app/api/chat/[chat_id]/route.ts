import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

interface Params{
  params: { chat_id: number }
}

async function getAccessToken(){
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  if (!token) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  return token
}

export async function GET(request: NextRequest, { params }: Params) { 
  try{
    const token = await getAccessToken()
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

export async function POST(request: NextRequest, { params }: Params){
  try{
    const token = await getAccessToken()
    const { chat_id } = await params

    const { messages } = await request.json();
    const lastUserMessage = messages[messages.length - 1];
    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    // 메세지 내부 attachment를 상위필드로 승격
    const disease_code = lastUserMessage?.attachment?.disease_code ?? null
    const product_id = lastUserMessage?.attachment?.product_id ?? null

    const data = new URLSearchParams()
    data.append('text', lastUserMessage.content)
    if (chat_id) {
      data.append('chat_id', String(chat_id));
    }
    if (disease_code != null) data.append("disease_code", disease_code);
    if (product_id != null)   data.append("product_id", product_id);

    const fastApiResponse = await fetch('http://API:8000/chat/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: data,
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