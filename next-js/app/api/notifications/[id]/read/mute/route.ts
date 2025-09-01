// /app/api/notifications/route.ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

const API = "http://API:8000";

async function getAccessToken(): Promise<string | null> {
  const store = await cookies();               // ✅ await
  return store.get("access_token")?.value ?? null;
}

export async function GET() {
  const token = await getAccessToken();
  if (!token) return new NextResponse("Unauthorized", { status: 401 });

  const upstream = await fetch(`${API}/notifications`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!upstream.ok) {
    const body = await upstream.text().catch(() => "");
    return new NextResponse(body || "Upstream error", { status: upstream.status });
  }

  const data = await upstream.json();
  return NextResponse.json(data);
}
