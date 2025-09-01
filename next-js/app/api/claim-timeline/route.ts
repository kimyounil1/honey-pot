// /app/api/claim-timeline/route.ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

const API = "http://API:8000";

async function getAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("access_token")?.value ?? null;
}

export async function GET() {
  const token = await getAccessToken();
  if (!token) return new NextResponse("Unauthorized", { status: 401 });

  const res = await fetch(`${API}/claim-timeline`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return new NextResponse(text || "Upstream error", { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}

export async function POST(req: Request) {
  const token = await getAccessToken();
  if (!token) return new NextResponse("Unauthorized", { status: 401 });

  const url = new URL(req.url);
  const force = url.searchParams.get("force");

  const res = await fetch(
    `${API}/claim-timeline/scan${force ? `?force=${force}` : ""}`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return new NextResponse(text || "Upstream error", { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
