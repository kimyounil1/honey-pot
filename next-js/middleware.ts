import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  const { pathname } = request.nextUrl;

  // 로그인이 안 된 사용자가 /chat에 접근하려는 경우
  if (!accessToken && pathname.startsWith("/chat")) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // 로그인이 된 사용자가 로그인, 회원가입, 또는 메인 페이지에 접근하려는 경우
  if (accessToken && (pathname === "/login" || pathname === "/signup" || pathname === "/")) {
    const url = request.nextUrl.clone();
    url.pathname = "/chat";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // 미들웨어를 적용할 경로를 지정합니다.
  matcher: ["/chat/:path*", "/login", "/signup", "/"],
};
