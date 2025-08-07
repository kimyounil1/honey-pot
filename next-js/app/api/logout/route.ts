import { NextResponse } from "next/server";

export async function GET() {
  // 응답 객체를 먼저 생성합니다.
  const response = NextResponse.redirect(new URL("/login", process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"));

  // 쿠키를 삭제합니다. (maxAge: 0)
  response.cookies.set("access_token", "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });

  return response;
}
