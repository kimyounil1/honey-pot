import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function GET(req: Request, { params }: { params: { chat_id: number } }){
    try{
        const id = params.chat_id
        if(!id){
            return new NextResponse('Chat ID is required', { status: 400 })
        }
        const cookieStore = cookies();
        const token = cookieStore.get('access_token')?.value

        if(!token){
            return new NextResponse('Unauthorized', { status: 401 })
        }
        const fastApiResponse = await fetch(`http://API:8000//chat/${id}/messages?access_token=${token}`,
            {
                method: 'GET',
                headers: {
                'Content-Type': 'application/json',
                // 'Authorization': `Bearer ${token}`, // 인증 토큰 전달z
                },
            }
        );
        if(!fastApiResponse.ok){
            const errorBody = await fastApiResponse.text()
            return new NextResponse(errorBody, { status: fastApiResponse.status })
        }
        const messages = await fastApiResponse.json()
        return NextResponse.json(messages)
    } catch(error){
        console.error('Error fetching chat history', error)
        if (error instanceof Error){
            return new NextResponse(error.message, { status: 500 });
        }
        return new NextResponse('An unknown error occurred.', { status: 500 });
    }
}