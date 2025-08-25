import { cookies } from 'next/headers';

export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    const { messages } = await req.json();
    const lastUserMessage = messages[messages.length - 1];

    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    // 메세지 내부 attachment를 상위필드로 승격
    const disease_code = lastUserMessage?.attachment?.disease_code ?? null
    const product_id = lastUserMessage?.attachment?.product_id ?? null

    const data = new URLSearchParams();
    data.append('text', lastUserMessage.content); 
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