import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function getTokenOr401() {
  const token = cookies().get("access_token")?.value;
  if (!token) return new NextResponse("Unauthorized", { status: 401 });
  return token;
}

export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const token = getTokenOr401();
  if (token instanceof NextResponse) return token;

  const res = await fetch(`http://API:8000/notifications/${params.id}/read`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    return new NextResponse(body, { status: res.status });
  }
  return NextResponse.json({ ok: true });
}
