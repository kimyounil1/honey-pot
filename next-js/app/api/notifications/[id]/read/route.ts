// /app/api/notifications/[id]/read/route.ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

const API = "http://API:8000";

async function readAccessToken(): Promise<string | null> {
  const store = await cookies(); // ✅ 반드시 await
  return store.get("access_token")?.value ?? null;
}

export async function POST(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const token = await readAccessToken();
  if (!token) return new NextResponse("Unauthorized", { status: 401 });

  const res = await fetch(`${API}/notifications/${params.id}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    return new NextResponse(body || "Upstream error", { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
