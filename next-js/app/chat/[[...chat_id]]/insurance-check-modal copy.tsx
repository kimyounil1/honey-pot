"use client";

import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2 } from "lucide-react";

export type InsuranceCheckModalProps = {
  isOpen: boolean;
  onClose: () => void;
  /** 커스텀 로더를 쓰고 싶으면 제공 (insurer 없이 전체 정책 리스트 반환) */
  fetchAllPolicies?: () => Promise<string[]>;
  /** 전체 정책을 반환하는 엔드포인트 (기본: /api/policies/list) */
  policiesEndpoint?: string;
  /** 모달 타이틀 커스터마이즈 */
  title?: string;
};

export default function InsuranceCheckModal({
  isOpen,
  onClose,
  fetchAllPolicies,
  policiesEndpoint = "/api/policies/my_policies",
  title = "나의 보험 확인하기",
}: InsuranceCheckModalProps) {
  // 목록/검색 상태
  const [policyIds, setPolicyIds] = useState<string[] | null>(null);
  const [policyIdsError, setPolicyIdsError] = useState<string | null>(null);
  const [policyIdsLoading, setPolicyIdsLoading] = useState(false);
  const [policyQuery, setPolicyQuery] = useState("");

  // 열릴 때 전체 정책 로드
  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;
    (async () => {
      setPolicyIds(null);
      setPolicyIdsError(null);
      setPolicyIdsLoading(true);
      try {
        let ids: string[] = [];

        if (fetchAllPolicies) {
          // fetchAllPolicies()가 string[]를 반환하더라도 혹시 몰라 정규화 + 중복제거
          const raw = await fetchAllPolicies();
          ids = Array.from(
            new Set(
              (raw ?? []).map((x: any) =>
                typeof x === "string"
                  ? x
                  : typeof x === "number"
                  ? String(x)
                  : String(x?.policy_id ?? x?.id ?? x)
              ).filter(Boolean)
            )
          );
        } else {
          const res = await fetch(policiesEndpoint, { cache: "no-store" });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const json = await res.json();

          // 백엔드 응답 키 유연 대응 + 정규화 + 중복제거
          const raw = Array.isArray(json?.policy_ids)
            ? json.policy_ids
            : Array.isArray(json?.policies)
            ? json.policies
            : [];

          ids = Array.from(
            new Set(
              (raw ?? []).map((x: any) =>
                typeof x === "string"
                  ? x
                  : typeof x === "number"
                  ? String(x)
                  : String(x?.policy_id ?? x?.id ?? x)
              ).filter(Boolean)
            )
          );
        }
        if (!cancelled) setPolicyIds(ids);
      } catch (e: any) {
        if (!cancelled) setPolicyIdsError(e?.message || "Failed to load policies");
      } finally {
        if (!cancelled) setPolicyIdsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, fetchAllPolicies, policiesEndpoint]);

  // 검색 필터
  const filteredPolicyIds = useMemo(() => {
    const q = policyQuery.trim().toLowerCase();
    if (!policyIds) return [] as string[];
    if (!q) return policyIds;
    return policyIds.filter((id) => id.toLowerCase().includes(q));
  }, [policyIds, policyQuery]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-xl">{title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <Input
            placeholder="보험 이름으로 검색"
            value={policyQuery}
            onChange={(e) => setPolicyQuery(e.target.value)}
          />
          <div className="text-sm text-muted-foreground">
            총 {policyIds?.length ?? 0}건 중 {filteredPolicyIds.length}건 표시
          </div>

          <ScrollArea className="h-72 rounded-md border p-2">
            {policyIdsLoading && (
              <div className="flex items-center justify-center py-10 text-sm">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 불러오는 중...
              </div>
            )}

            {!policyIdsLoading && policyIdsError && (
              <div className="text-sm text-destructive">{policyIdsError}</div>
            )}

            {!policyIdsLoading && !policyIdsError && filteredPolicyIds.length === 0 && (
              <div className="text-sm text-muted-foreground">검색 결과가 없습니다.</div>
            )}

            <div className="grid grid-cols-1 gap-2">
              {Array.from(new Set((filteredPolicyIds ?? []).map(String))).map((pid) => (
                <button
                  key={pid}
                  className="flex items-center justify-between rounded-2xl border p-3 hover:shadow-sm active:scale-[0.99] transition"
                >
                  <div className="truncate mr-3">{pid}</div>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
