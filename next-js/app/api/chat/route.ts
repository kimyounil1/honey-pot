import { cookies } from 'next/headers';

export const maxDuration = 30

export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    const { messages, attachment_ids, chat_id } = await req.json();
    const lastUserMessage = messages[messages.length-1];

    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    const fastApiPayload: any = {
      role: lastUserMessage.role,
      text: lastUserMessage.content,
      attachment_ids: attachment_ids,
      first_message: true
    }

    if(chat_id){
      fastApiPayload.chat_id = chat_id;
      fastApiPayload.first_message = false;
    }
    
    const fastApiResponse = await fetch(`http://API:8000/chat/ask?access_token=${token}`,
    {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        // 'Authorization': `Bearer ${token}`, // 인증 토큰 전달
      },
      body: JSON.stringify(fastApiPayload),
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      console.error('FastAPI backend returned an error:', errorBody);
      return new Response(errorBody, { status: fastApiResponse.status });
    }
    return new Response(fastApiResponse.body, {
      status: fastApiResponse.status,
      statusText: fastApiResponse.statusText,
      headers: fastApiResponse.headers,
    });
    } catch (error) {
    console.error('Error in Next.js API route (/api/chat):', error);
    if (error instanceof Error) {
      return new Response(error.message, { status: 500 });
    }
    return new Response('An unknown error occurred.', { status: 500 });
  }
}