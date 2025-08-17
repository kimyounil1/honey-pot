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

    const { messages, attachment_ids } = await request.json();
    const lastUserMessage = messages[messages.length - 1];
    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    const formData = new URLSearchParams()
    formData.append('text', lastUserMessage.content)
    if (attachment_ids) {
      formData.append('attachment_ids', JSON.stringify(attachment_ids));
    }
    if (chat_id) {
      formData.append('chat_id', String(chat_id));
    }

    const fastApiResponse = await fetch('http://API:8000/chat/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
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