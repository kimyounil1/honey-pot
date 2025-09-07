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

export async function GET(_: Request, ctx: { params: Promise<{ assessment_id: string }> }) {
  try {
    const token = await getAccessToken();
    if (token instanceof NextResponse) return token;
    const { assessment_id } = await ctx.params;
    const r = await fetch(`http://API:8000/assessments/${assessment_id}/messages`, {
      headers: { 'Accept': 'application/json', 'Authorization': `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!r.ok) return new NextResponse(await r.text(), { status: r.status });
    return NextResponse.json(await r.json());
  } catch (e) {
    return new NextResponse('Internal error', { status: 500 });
  }
}

export async function POST(request: Request, ctx: { params: Promise<{ assessment_id: string }> }) {
  try {
    const token = await getAccessToken();
    if (token instanceof NextResponse) return token;
    const body = await request.json();
    const { assessment_id } = await ctx.params;
    const r = await fetch(`http://API:8000/assessments/${assessment_id}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) return new NextResponse(await r.text(), { status: r.status });
    return NextResponse.json(await r.json());
  } catch (e) {
    return new NextResponse('Internal error', { status: 500 });
  }
}
