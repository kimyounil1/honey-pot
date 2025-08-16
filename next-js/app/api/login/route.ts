export const runtime = "nodejs";

import { NextResponse } from "next/server";

export async function POST(req: Request) {
  // const body = await req.json();
  const formData = await req.formData()

  const body = new URLSearchParams()
  body.append("username", formData.get("username") as string)
  body.append("password", formData.get("password") as string)

  const res = await fetch("http://API:8000/users/login", {
    method: "POST",
    // headers: { "Content-Type": "application/json" },
    // body: JSON.stringify(body),
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: body.toString(),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ error: "Invalid credentials" }))
    return NextResponse.json(errorData, { status: res.status })
  }

  const data = await res.json();
  const response = NextResponse.json({ success: true });

  // HttpOnly 쿠키 설정
  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    path: "/",
    maxAge: 60 * 60, // 1 hour
    secure: process.env.NODE_ENV === "production",
  });

  return response;
}
