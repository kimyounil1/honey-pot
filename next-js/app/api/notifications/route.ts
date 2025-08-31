import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

function getTokenOr401() {
  const token = cookies().get("access_token")?.value;
  if (!token) return new NextResponse("Unauthorized", { status: 401 });
  return token;
}

export async function GET() {
  const token = getTokenOr401();
  if (token instanceof NextResponse) return token;

  const res = await fetch("http://API:8000/notifications/", {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    return new NextResponse(body, { status: res.status });
  }
  const data = await res.json();
  return NextResponse.json(data);
}
