import { NextResponse } from "next/server";

export async function GET() {
  // 응답 객체를 먼저 생성합니다.
  const baseUrl = process.env.BASE_URL
  // const response = NextResponse.redirect(new URL("/", process.env.NEXT_PUBLIC_BASE_URL || "http://54.252.129.84:3000"));
  const response = NextResponse.redirect(new URL("/", baseUrl));

  // 쿠키를 삭제합니다. (maxAge: 0)
  response.cookies.set("access_token", "", {
    httpOnly: true,
    path: "/",
  });
    maxAge: 0

  return response;
}
