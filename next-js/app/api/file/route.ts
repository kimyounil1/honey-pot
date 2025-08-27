import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from "next/server";

/**
 * 파일 업로드를 FastAPI로 프록시하는 라우트
 * - 클라이언트 -> (multipart/form-data) -> Next.js -> FastAPI
 * - FastAPI의 응답을 상태/헤더 포함 그대로 전달
 */

// 업로드/스트리밍은 Edge에서 제약이 있으므로 Node 런타임 권장
export const runtime = "nodejs";

async function getAccessToken(){
  const cookieStore = await cookies();
  const token = cookieStore.get('access_token')?.value;
  if (!token) {
    return new NextResponse('Unauthorized', { status: 401 });
  }
  return token
}

export async function POST(req: NextRequest) {
  try {
    // 1) 클라이언트가 보낸 formData 수신
    const inForm = await req.formData();
    const file = inForm.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json(
        { detail: "file 필드가 필요합니다." },
        { status: 400 }
      );
    }

    // 2) FastAPI로 보낼 formData 구성 (파일만 넘기면 됨)
    const outForm = new FormData();
    // filename을 유지하려면 세 번째 인자로 이름을 다시 지정
    outForm.append("file", file, (file as any).name);

    const token = await getAccessToken();

    // 4) 타임아웃/취소 제어
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 300_000); // 300초

    // 5) FastAPI에 프록시 요청
    const res = await fetch(`http://API:8000/ocr/`, {
      method: "POST",
      headers: {
        // 'Content-Type': 'multipart/form-data',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: outForm,
      signal: controller.signal,
      // 업로드/폴링은 항상 최신 상태 필요
      cache: "no-store",
    }).finally(() => clearTimeout(timeout));

    // 6) FastAPI 응답을 그대로 전달
    const contentType = res.headers.get("content-type") ?? ""
    // console.log("#######[DEBUG]upload result: ", data, "#######");

    // 필요한 최소한의 캐시 무효화 헤더 추가
    return new NextResponse(res.body, {
      status: res.status,
      headers: {
        "content-type": contentType,
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
      },
    });
  } catch (e: any) {
    // 프록시 단계에서 진짜 예외일 때만 500
    return NextResponse.json({ detail: e?.message ?? "proxy error" }, { status: 500 });
  }
}
