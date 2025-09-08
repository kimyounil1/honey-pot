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
      // Demo completed claims corresponding to assessment samples #2 and #3
      { claim_id: 9004, policy_id: 202, claim_date: "2025-08-18", claimed_amount: 180000, approved_amount: 150000, status: "COMPLETED" },
      { claim_id: 9005, policy_id: 203, claim_date: "2025-08-15", claimed_amount: 320000, approved_amount: 290000, status: "COMPLETED" },
    ],
    assessable: [
      { id: 1, title: "자동차보험 보상 문의", insurer: "롯데손해보험", created_at: "2025-01-09T10:30:00Z" },
      { id: 2, title: "추돌사고 휴업손해 문의", insurer: "현대해상", created_at: "2025-01-08T15:20:00Z" },
      { id: 3, title: "렌트카 비용 보상 문의", insurer: "삼성화재", created_at: "2025-01-07T09:15:00Z" },
    ],
  });
}
