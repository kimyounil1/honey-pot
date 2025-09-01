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
  deadline_date: string;
  is_muted?: boolean;
};

async function fetchJSON<T>(url: string, init?: RequestInit) {
  const r = await fetch(url, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
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

        // ✅ 읽음 여부와 무관하게 그대로 사용 (백엔드에서 이미 mute만 필터)
        setNotis(ns);
        setTimelines(ts);
        setOpen(ns.length > 0); // ✅ unread 조건 제거
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

  const relatedIds = useMemo(() => new Set(notis.map((n) => n.timeline_id)), [notis]);

  const totalAmount = useMemo(() => {
    return timelines
      .filter((t) => relatedIds.has(t.id))
      .reduce((acc, t) => acc + (t.expected_amount ?? 0), 0);
  }, [relatedIds, timelines]);

  const earliestDeadline = useMemo(() => {
    return timelines
      .filter((t) => relatedIds.has(t.id))
      .map((t) => t.deadline_date)
      .sort()[0];
  }, [relatedIds, timelines]);

  if (loading || !open || notis.length === 0) return null;

  // 닫기: 읽음 처리 여부는 선택.
  // 요구사항: 읽어도 로그인 시 다시 떠야 하므로 굳이 mark_read 안 해도 됨.
  const onCloseOnly = async () => {
    setOpen(false);
    // 필요하면 읽음 처리 유지:
    // await Promise.all(notis.map((n) => fetch(`/api/notifications/${n.id}/read`, { method: "POST" })));
  };

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
          <div className="text-sm text-gray-500 mb-1">청구 마감 알림</div>
          <div className="text-base md:text-lg font-semibold">
            환급 예상 합계{" "}
            <span className="text-emerald-600">
              {totalAmount.toLocaleString()} 원
            </span>
            {earliestDeadline ? (
              <>
                {" "}
                · 가장 빠른 마감일{" "}
                <span className="text-rose-600">{earliestDeadline}</span>
              </>
            ) : null}
          </div>
          <div className="text-sm text-gray-600 mt-1">
            {notis[0]?.title} — {notis[0]?.message}
            {notis.length > 1 ? ` 외 ${notis.length - 1}건` : ""}
          </div>
        </div>

        <div className="flex gap-2">
          <a
            href="/chat"
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
