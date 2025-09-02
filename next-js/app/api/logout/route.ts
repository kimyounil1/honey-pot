// app/api/logout/route.ts
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  // 요청에서 확실한 절대 origin 확보
  // const { origin } = new URL(req.url);

  // 리다이렉트 응답 생성
  // const res = NextResponse.redirect(new URL("/", origin));

  const res = new NextResponse(null, { status: 204 })

  // 로그인 쿠키들 제거 (필요한 이름 모두)
  const cookieOpts = {
    path: "/",
    httpOnly: true as const,
    sameSite: "lax" as const,
    maxAge: 0,
    expires: new Date(0),
    // secure: process
  };
  res.cookies.set("access_token", "", cookieOpts);
  // refresh_token을 쓰고 있다면 같이 삭제
  res.cookies.set("refresh_token", "", cookieOpts);

  return res;
}
