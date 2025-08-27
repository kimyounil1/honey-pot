// /next-js/app/api/chat/chats/route.ts
import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(req: NextRequest, ctx: { params: Promise<{ insurer: string }> }) { 
  try {
    const { insurer } = await ctx.params
    const fastApiResponse = await fetch(`http://API:8000/policies/${insurer}/list`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
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