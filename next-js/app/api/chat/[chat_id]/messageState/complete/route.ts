// /next-js/app/api/chat/[chat_id]/messageState/route.ts
import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

async function getAccessToken(){
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  if (!token) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  return token
}

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest, ctx: { params: Promise<{ chat_id: string }> }){
    try {

        const tokenOrRes = await getAccessToken();
        if (tokenOrRes instanceof NextResponse) {
            // 401 등 응답을 그대로 반환
            return tokenOrRes;
        }
        const token = tokenOrRes
        const { chat_id } = await ctx.params;
        const fastApiResponse = await fetch(`http://API:8000/chat/${chat_id}/messageState/complete`, {
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
        console.log("MessageState from FastAPI:", responseBody)
        return NextResponse.json(responseBody, {
            headers: {
                'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            },
        })
    } catch(error){
        console.error('Error in Next.js API route (/api/chat/[chat_id]/messageState):',error)
        if(error instanceof Error){
            return new NextResponse(error.message, { status: 500 })
        }
        return new NextResponse('An unknown error occured.', { status: 500 })
    }
}