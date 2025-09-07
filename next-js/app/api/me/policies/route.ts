import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

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

export async function GET() {
  try {
    const token = await getAccessToken();
    if (token instanceof NextResponse) return token;

    const fastApiResponse = await fetch('http://API:8000/me/policies', {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      cache: 'no-store',
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      console.error('FastAPI backend returned an error:', errorBody);
      return new NextResponse(errorBody, { status: fastApiResponse.status });
    }

    const responseBody = await fastApiResponse.json();
    // Ensure id is a number (defensive in case backend changes)
    const normalized = Array.isArray(responseBody)
      ? responseBody.map((p: any) => ({ id: Number(p.id), policy_id: p.policy_id, insurer: p.insurer }))
      : responseBody;
    return NextResponse.json(normalized);
  } catch (error) {
    console.error('Error in Next.js API route (/api/me/policies):', error);
    if (error instanceof Error) {
      return new NextResponse(error.message, { status: 500 });
    }
    return new NextResponse('An unknown error occurred.', { status: 500 });
  }
}
