// import { openai } from "@ai-sdk/openai"
// import { streamText } from "ai"

export const maxDuration = 30

export async function POST(req: Request) {
  try {

    const { messages, user_id, first_message, attachment_ids } = await req.json();
    const lastUserMessage = messages[messages.length-1];

    if (!lastUserMessage || lastUserMessage.role !== 'user') {
      return new Response('Valid user message not found in the request body.', { status: 400 });
    }

    const fastApiPayload = {
      user_id: user_id,
      text: lastUserMessage.content,
      first_message: first_message,
      attachment_ids: attachment_ids,
    }
    
    const fastApiResponse = await fetch("http:///API:8000/chat/ask",{
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
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