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

export const runtime = "nodejs"; // 내부 네트워크/쿠키 포워딩을 위해 Node 런타임 권장

export async function POST(request: Request) {
  try {
    const token = await getAccessToken()
    let body: any;
    try {
        body = await request.json()
    } catch {
        return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
    }

    // 필수값 수동검증
    const policyId = typeof body?.policy_id === "string" ? body.policy_id.trim() : "";
    if (!policyId) {
      return NextResponse.json({ error: "policyId is required" }, { status: 400 });
    }

    // 4) FastAPI로 프록시
    const upstream = await fetch(`http://API:8000/policies/submit`, {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ policy_id: policyId }),
      cache: "no-store",
    });

    const ct = upstream.headers.get("content-type") ?? "";
    const status = upstream.status;

    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      if (ct.includes("application/json")) {
        return new NextResponse(text, {
          status,
          headers: { "Content-Type": "application/json" },
        });
      }
      return NextResponse.json(
        { error: `Upstream error: HTTP ${status}`, detail: text || null },
        { status }
      );
    }

    if (ct.includes("application/json")) {
      const data = await upstream.json();
      return NextResponse.json(data, { status });
    } else {
      const text = await upstream.text();
      return new NextResponse(text, {
        status,
        headers: { "Content-Type": ct || "text/plain; charset=utf-8" },
      });
    }
  } catch (err: any) {
    console.error("[/api/policies/submit] error:", err);
    return NextResponse.json(
      { error: "Internal Server Error", detail: err?.message ?? null },
      { status: 500 }
    );
  }
}