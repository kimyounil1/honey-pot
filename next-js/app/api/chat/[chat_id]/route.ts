import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest, { params }: { params: { chat_id: string } }) { 
  try {
    const { chat_id } = params;
    const cookieStore = await cookies();
    const token = cookieStore.get('access_token')?.value;

    if (!token) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

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