// /next-js/app/api/chat/chats/route.ts
import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

async function getAccessToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  if (!token) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  return token;
}
export const dynamic = 'force-dynamic';
export const revalidate = 0;
export async function GET(request: NextRequest) { 
  try {
    const token = await getAccessToken();
    
    if (token instanceof NextResponse) {
        return token;
    }

    const fastApiResponse = await fetch(`http://API:8000/chat/chats`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      cache: "no-store"
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      console.error('FastAPI backend returned an error:', errorBody);
      return new NextResponse(errorBody, { status: fastApiResponse.status });
    }

    const responseBody = await fastApiResponse.json();
    return NextResponse.json(responseBody);

  } catch (error) {
    console.error('Error in Next.js API route (/api/chat/chats):', error);
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('An unknown error occurred.', { status: 500 });
  }
}
