import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

async function getAccessToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  if (!token) return new NextResponse('Unauthorized', { status: 401 });
  return token;
}

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const token = await getAccessToken();
    if (token instanceof NextResponse) return token;
    const r = await fetch('http://API:8000/assessments', {
      headers: { 'Accept': 'application/json', 'Authorization': `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!r.ok) return new NextResponse(await r.text(), { status: r.status });
    return NextResponse.json(await r.json());
  } catch (e) {
    return new NextResponse('Internal error', { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const token = await getAccessToken();
    if (token instanceof NextResponse) return token;
    const body = await request.json();

    const fastApiResponse = await fetch('http://API:8000/assessments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (!fastApiResponse.ok) {
      const errorBody = await fastApiResponse.text();
      return new NextResponse(errorBody, { status: fastApiResponse.status });
    }
    const json = await fastApiResponse.json();
    return NextResponse.json(json);
  } catch (e) {
    console.error('Error in /api/assessments', e);
    return new NextResponse('Internal error', { status: 500 });
  }
}
