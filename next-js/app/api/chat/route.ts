import { cookies } from 'next/headers';

export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    const { messages, attachment_ids } = await req.json();
    const lastUserMessage = messages[messages.length - 1];

    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    const formData = new URLSearchParams();
    formData.append('text', lastUserMessage.content);
    if (attachment_ids) {
      formData.append('attachment_ids', JSON.stringify(attachment_ids));
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