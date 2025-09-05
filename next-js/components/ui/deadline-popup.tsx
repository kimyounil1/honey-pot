// app/chat/DeadlinePopup.tsx
"use client";

import { useEffect, useMemo, useState, useLayoutEffect } from "react";

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

const MS_DAY = 86400000;
const daysLeft = (d: string) => {
  const end = new Date(d).setHours(0, 0, 0, 0);
  const now = new Date().setHours(0, 0, 0, 0);
  return Math.ceil((end - now) / MS_DAY);
};

export default function DeadlinePopup() {
  const [open, setOpen] = useState(false);
  const [notis, setNotis] = useState<Notification[]>([]);
  const [timelines, setTimelines] = useState<Timeline[]>([]);
  const [loading, setLoading] = useState(true);

  // ✅ 앵커(메인 카드) 크기/좌표 추적
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
  useLayoutEffect(() => {
    const el = document.querySelector(
      '[data-popup-anchor="main-card"]'
    ) as HTMLElement | null;

    if (!el) {
      setAnchorRect(null); // 앵커 없으면 중앙 고정(폴백)
      return;
    }

    const update = () => setAnchorRect(el.getBoundingClientRect());
    update();

    const ro = new ResizeObserver(update);
    ro.observe(el);
    window.addEventListener("resize", update);

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", update);
    };
  }, []);

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

        // 🔸 D-14 이내 타임라인이 있으면 알림 없어도 팝업 오픈
        const urgent = ts.filter(
          (t) =>
            !t.is_muted &&
            daysLeft(t.deadline_date) >= 0 &&
            daysLeft(t.deadline_date) <= 14
        );
        setOpen(ns.length > 0 || urgent.length > 0);
      } catch {
        // 로그인 전/알림 없음은 무시
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const relatedIds = useMemo(
    () => new Set(notis.map((n) => n.timeline_id)),
    [notis]
  );

  const totalAmount = useMemo(() => {
    return timelines
      .filter((t) => relatedIds.has(t.id))
      .reduce((acc, t) => acc + (t.expected_amount ?? 0), 0);
  }, [relatedIds, timelines]);

  const earliest = useMemo(() => {
    const list = timelines
      .filter((t) => relatedIds.has(t.id))
      .map((t) => t.deadline_date)
      .sort();
    return list[0];
  }, [relatedIds, timelines]);

  if (loading || !open || (notis.length === 0 && !earliest)) return null;

  const dday = earliest ? daysLeft(earliest) : null;

  const onCloseOnly = async () => {
    setOpen(false);
  };

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

  // ✅ 앵커가 있으면 그 좌표/폭으로 고정, 없으면 중앙 정렬 폴백
  const fixedStyle: React.CSSProperties = anchorRect
    ? {
      left: `${Math.round(anchorRect.left)}px`,
      width: `${Math.round(anchorRect.width)}px`,
      transform: "none",
    }
    : {};

  return (
    <div
      className="fixed bottom-4 md:bottom-6 z-50 left-1/2 -translate-x-1/2"
      style={fixedStyle}
    >
      <div className="rounded-2xl border shadow-lg bg-white/95 backdrop-blur p-4 md:p-5 flex flex-col md:flex-row items-start md:items-center gap-3 w-full">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <div className="text-sm text-gray-500">청구 마감 알림</div>
            {dday != null && dday >= 0 && (
              <span className="text-xs font-semibold text-rose-600 border border-rose-200 bg-rose-50 px-2 py-0.5 rounded-full">
                D-{dday}
              </span>
            )}
          </div>

          <div className="text-base md:text-lg font-semibold">
            환급 예상 합계{" "}
            <span className="text-emerald-600">
              {totalAmount.toLocaleString()} 원
            </span>{" "}
            · 가장 빠른 마감일{" "}
            <span className="text-rose-600">{earliest ?? "-"}</span>
          </div>

          <div className="text-sm text-gray-600 mt-1">
            보험 청구 마감일까지{" "}
            <b className="text-gray-900">
              {dday != null && dday >= 0 ? `D-${dday}` : "-"}
            </b>{" "}
            남았습니다. 꿀통에서 자동 청구하고 받아가세요!
          </div>
        </div>

        <div className="flex gap-2">
          <a
            href="/refund"
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
