"use client";

import { useEffect, useMemo, useState } from "react";

type Notification = {
  id: number;
  timeline_id: number;
  send_on: string;
  deadline_date: string;
  title: string;
  message: string;
  is_read: boolean;
  priority: number;
};

type Timeline = {
  id: number;
  expected_amount: number | null;
  deadline_date: string; // YYYY-MM-DD ISO 가정
  is_muted?: boolean;
};

async function fetchJSON<T>(url: string, init?: RequestInit) {
  const r = await fetch(url, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
}

function daysLeft(deadlineISO?: string | null) {
  if (!deadlineISO) return null;
  const end = new Date(deadlineISO).setHours(0, 0, 0, 0);
  const today = new Date().setHours(0, 0, 0, 0);
  return Math.ceil((end - today) / (1000 * 60 * 60 * 24));
}

export default function DeadlinePopup() {
  const [open, setOpen] = useState(false);
  const [notis, setNotis] = useState<Notification[]>([]);
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [ns, ts] = await Promise.all([
          fetchJSON<Notification[]>("/api/notifications"),
          fetchJSON<Timeline[]>("/api/claim-timeline"),
        ]);
        if (!mounted) return;

        setNotis(ns);
        setTimelines(ts);
      } catch {
        // 로그인 전/알림 없음 → 무시
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // 알림과 연관된 타임라인만 집계
  const relatedIds = useMemo(() => new Set(notis.map((n) => n.timeline_id)), [notis]);

  const totalAmount = useMemo(() => {
    return timelines
      .filter((t) => relatedIds.has(t.id))
      .reduce((acc, t) => acc + (t.expected_amount ?? 0), 0);
  }, [relatedIds, timelines]);

  const earliestDeadline = useMemo(() => {
    const list = timelines.filter((t) => relatedIds.has(t.id)).map((t) => t.deadline_date);
    if (list.length === 0) return null;
    // YYYY-MM-DD면 문자열 정렬로 충분
    return list.sort()[0] ?? null;
  }, [relatedIds, timelines]);

  const earliestD = useMemo(() => (earliestDeadline ? daysLeft(earliestDeadline) : null), [earliestDeadline]);

  // D-14부터 계속 표시
  useEffect(() => {
    if (loading) return;
    setOpen(notis.length > 0 && earliestD !== null && earliestD <= 14);
  }, [loading, notis.length, earliestD]);

  if (loading || !open || notis.length === 0) return null;

  // 닫기
  const onCloseOnly = async () => setOpen(false);

  // 다시 보지 않기: 관련 타임라인 모두 mute
  const onNeverShow = async () => {
    try {
      await Promise.all(
        Array.from(relatedIds).map((id) =>
          fetch(`/api/claim-timeline/${id}/mute`, { method: "POST" })
        )
      );
    } catch {}
    setOpen(false);
  };

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 px-4 md:px-6">
      <div className="mx-auto max-w-3xl rounded-2xl border shadow-lg bg-white/95 backdrop-blur p-4 md:p-5 flex flex-col md:flex-row items-start md:items-center gap-3">
        <div className="flex-1">
          {/* 상단 라벨 + D-배지(빨간색) */}
          <div className="text-sm text-gray-500 mb-1 flex items-center gap-2">
            청구 마감 알림
            {typeof earliestD === "number" && (
              <span className="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-600">
                D-{Math.max(0, earliestD)}
              </span>
            )}
          </div>

          {/* 합계 · 가장 빠른 마감일 (여기서는 D-배지 제거) */}
          <div className="text-base md:text-lg font-semibold">
            환급 예상 합계{" "}
            <span className="text-emerald-600">{totalAmount.toLocaleString()} 원</span>
            {earliestDeadline ? (
              <>
                {" "}&middot; 가장 빠른 마감일{" "}
                <span className="text-rose-600">{earliestDeadline}</span>
              </>
            ) : null}
          </div>

          {/* 하단 문구: 줄바꿈, '외 N건' 제거 */}
          {typeof earliestD === "number" && (
            <div className="text-sm text-gray-600 mt-1 leading-relaxed">
              <div>
                보험 청구 마감일까지{" "}
                <b className="text-rose-600">D-{Math.max(0, earliestD)}</b> 남았습니다.
              </div>
              <div>꿀통에서 자동 청구하고 받아가세요!</div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <a
            href="/refund?from=deadline"
            className="inline-flex items-center rounded-xl bg-amber-500 text-white px-4 py-2 text-sm font-medium shadow hover:bg-amber-600"
          >
            지금 확인하기
          </a>
          <button
            onClick={onNeverShow}
            className="inline-flex items-center rounded-xl border px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            title="해당 마감 타임라인을 앞으로 표시하지 않습니다."
          >
            다시 보지 않기
          </button>
          <button
            onClick={onCloseOnly}
            className="inline-flex items-center rounded-xl border px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
