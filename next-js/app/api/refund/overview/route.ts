// app/api/refund/overview/route.ts
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    timelines: [
      { id: 101, insurer: "한화생명", policy_id: "무배당 2022", base_date: "2025-08-12", deadline_date: "2025-09-11", expected_amount: 249000 },
      { id: 102, insurer: "삼성화재", policy_id: "실손",      base_date: "2025-08-28", deadline_date: "2025-09-27", expected_amount: 33000  },
    ],
    claims: [
      { claim_id: 9001, policy_id: 101, claim_date: "2025-08-29", claimed_amount: 12000, approved_amount: null, status: "SUBMITTED" },
      { claim_id: 9002, policy_id: 102, claim_date: "2025-08-20", claimed_amount: 45000, approved_amount: null, status: "UNDER_REVIEW" },
      { claim_id: 9003, policy_id: 102, claim_date: "2025-08-10", claimed_amount: 45000, approved_amount: 30000, status: "COMPLETED" },
    ],
    assessable: [
      { id: 5001, title: "자동차 보상 문의", insurer: "A손해보험", created_at: "2025-01-09T10:30:00Z" },
    ],
  });
}

