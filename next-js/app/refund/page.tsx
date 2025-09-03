// app/refund/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, TrendingUp, ShieldCheck } from "lucide-react";

type TimelineItem = {
  id: number;
  policy_id?: string | null;
  insurer?: string | null;
  disease_name?: string | null;
  disease_code?: string | null;
  base_date: string;
  deadline_date: string;
  expected_amount?: string | number | null;
  currency?: string | null;
};

type ClaimItem = {
  claim_id: number;
  policy_id: number;
  claim_date?: string | null;
  claimed_amount?: number | null;
  approved_amount?: number | null;
  status?: string | null; // 'SUBMITTED' | 'UNDER_REVIEW' 등
};

export default function RefundDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [timelines, setTimelines] = useState<TimelineItem[]>([]);
  const [claims, setClaims] = useState<ClaimItem[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/refund/overview", { cache: "no-store" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        setTimelines(data.timelines ?? []);
        setClaims(data.claims ?? []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const grouped = useMemo(() => {
    const pending = claims.filter((c) => (c.status ?? "").toUpperCase() === "SUBMITTED");
    const reviewing = claims.filter((c) => (c.status ?? "").toUpperCase() === "UNDER_REVIEW");
    const available = timelines;
    return { available, pending, reviewing, allCount: available.length + pending.length + reviewing.length };
  }, [timelines, claims]);

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center gap-2 text-gray-600">
          <Loader2 className="h-5 w-5 animate-spin" />
          불러오는 중…
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <section className="bg-gradient-to-br from-orange-50 to-yellow-50 border-b">
        <div className="container mx-auto px-4 py-10">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">환급금 찾기</h1>
          <p className="text-gray-600">내가 받을 수 있는 항목과 진행 상태를 한눈에 확인하세요.</p>
        </div>
      </section>

      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="all" className="w-full">
          <div className="flex items-center justify-between mb-4">
            <TabsList className="bg-white shadow-sm">
              <TabsTrigger value="all">
                전체 <Badge variant="secondary" className="ml-2">{grouped.allCount}</Badge>
              </TabsTrigger>
              <TabsTrigger value="available">
                청구가능 <Badge className="ml-2 bg-orange-500">{grouped.available.length}</Badge>
              </TabsTrigger>
              <TabsTrigger value="pending">
                청구중 <Badge className="ml-2 bg-amber-500">{grouped.pending.length}</Badge>
              </TabsTrigger>
              <TabsTrigger value="reviewing">
                보험심사중 <Badge className="ml-2 bg-yellow-600">{grouped.reviewing.length}</Badge>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="all" className="space-y-8">
            <SectionAvailable items={grouped.available} />
            <SectionPending items={grouped.pending} />
            <SectionReviewing items={grouped.reviewing} />
          </TabsContent>

          <TabsContent value="available">
            <SectionAvailable items={grouped.available} />
          </TabsContent>

          <TabsContent value="pending">
            <SectionPending items={grouped.pending} />
          </TabsContent>

          <TabsContent value="reviewing">
            <SectionReviewing items={grouped.reviewing} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

/** ▼▼ “청구가능” 섹션: 요약 칩이 섹션 하단에서 4초마다 부드럽게 순환 표시됩니다. */
function SectionAvailable({ items }: { items: TimelineItem[] }) {
  if (!items?.length) return <Empty label="청구가능 항목이 없어요." />;
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-orange-500" /> 청구가능
      </h2>

      {/* 순환 요약 칩 */}
      <RotatingHighlight items={items} intervalMs={4000} />

      <div className="grid md:grid-cols-2 gap-4">
        {items.map((it) => {
          const dday = daysLeft(it.deadline_date);
          return (
            <Card key={it.id} className="border-0 shadow-sm hover:shadow-md transition-all">
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-gray-900">
                  {it.insurer ?? "보험사 미지정"} · {it.policy_id ?? "상품코드 미지정"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-gray-700">
                <div className="flex items-center gap-2">
                  <Badge className="bg-orange-500">청구가능</Badge>
                  {it.disease_name && (
                    <span>
                      {it.disease_name}
                      {it.disease_code ? ` (${it.disease_code})` : ""}
                    </span>
                  )}
                </div>
                <div>
                  기산일: <b>{fmtDate(it.base_date)}</b> · 마감일: <b>{fmtDate(it.deadline_date)}</b>
                  {dday >= 0 && <Badge variant="secondary" className="ml-2">D-{dday}</Badge>}
                </div>
                {it.expected_amount && (
                  <div>
                    예상 환급액: <b>{num(it.expected_amount)}원</b>
                  </div>
                )}
                <div className="pt-2 flex gap-2">
                  <Button size="sm" className="bg-gradient-to-r from-orange-400 to-orange-500 text-white">
                    바로 청구하기
                  </Button>
                  <Button size="sm" variant="outline">
                    채팅으로 확인
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function SectionPending({ items }: { items: ClaimItem[] }) {
  if (!items?.length) return <Empty label="청구중인 항목이 없어요." />;
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">청구중</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {items.map((c) => (
          <Card key={c.claim_id} className="border-0 shadow-sm hover:shadow-md transition-all">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-gray-900">청구 ID #{c.claim_id}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-700 space-y-1">
              <div>청구일: <b>{fmtDate(c.claim_date)}</b></div>
              {c.claimed_amount != null && <div>청구액: <b>{num(c.claimed_amount)}원</b></div>}
              <div className="flex items-center gap-2"><Badge className="bg-amber-500">청구중</Badge></div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function SectionReviewing({ items }: { items: ClaimItem[] }) {
  if (!items?.length) return <Empty label="보험심사중인 항목이 없어요." />;
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-yellow-600" /> 보험심사중
      </h2>
      <div className="grid md:grid-cols-2 gap-4">
        {items.map((c) => (
          <Card key={c.claim_id} className="border-0 shadow-sm hover:shadow-md transition-all">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-gray-900">청구 ID #{c.claim_id}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-gray-700 space-y-1">
              <div>접수일: <b>{fmtDate(c.claim_date)}</b></div>
              <div className="flex items-center gap-2"><Badge className="bg-yellow-600">보험심사중</Badge></div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/** ▼▼ 섹션 하단에서 4초마다 부드럽게 넘어가는 요약 칩 */
function RotatingHighlight({ items, intervalMs = 4000 }: { items: TimelineItem[]; intervalMs?: number }) {
  const safeItems = items.filter((i) => i.deadline_date || i.expected_amount != null);
  if (safeItems.length === 0) return null;

  const [idx, setIdx] = useState(0);
  const [show, setShow] = useState(true);

  useEffect(() => {
    if (safeItems.length === 1) return;
    const timer = setInterval(() => {
      // 간단한 페이드/슬라이드 아웃 후 인
      setShow(false);
      const t = setTimeout(() => {
        setIdx((i) => (i + 1) % safeItems.length);
        setShow(true);
      }, 220); // out duration과 맞춤
      return () => clearTimeout(t);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [safeItems.length, intervalMs]);

  const it = safeItems[idx];
  const dday = daysLeft(it.deadline_date);

  return (
    <div
      aria-live="polite"
      className={[
        "inline-flex items-center gap-3 rounded-full border bg-white/90 px-3 py-1.5 shadow-sm",
        "text-xs md:text-sm",
        "transition-all duration-300",
        show ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1",
      ].join(" ")}
    >
      <span className="text-gray-600">예상 합계</span>
      <span className="font-semibold text-emerald-600">{num(it.expected_amount ?? 0)}원</span>
      <span className="text-gray-400">·</span>
      <span className="text-gray-600">가장 빠른 마감일</span>
      <span className="font-semibold text-rose-600">{fmtDate(it.deadline_date)}</span>
      {dday >= 0 && (
        <span className="ml-1 inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] md:text-xs text-gray-700">
          D-{dday}
        </span>
      )}
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <div className="text-sm text-gray-500">{label}</div>;
}

function fmtDate(d?: string | null) {
  if (!d) return "-";
  try {
    return new Date(d).toISOString().slice(0, 10);
  } catch {
    return d as string;
  }
}

function daysLeft(deadline?: string | null) {
  if (!deadline) return -1;
  const end = new Date(deadline).getTime();
  const now = new Date().setHours(0, 0, 0, 0);
  return Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)));
}

function num(v?: string | number | null) {
  const n = typeof v === "string" ? parseFloat(v) : v ?? 0;
  return isNaN(n as number) ? String(v ?? "") : (n as number).toLocaleString();
}
