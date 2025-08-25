"use client";

import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, ChevronLeft, Plus, Check } from "lucide-react";

export type InsurersResponse = { insurers: string[] };

export type InsurancePickerModalProps = {
  isOpen: boolean;
  onClose: () => void;

  /** 제출이 끝난 뒤 부모 쪽에 알려주고 싶을 때 */
  onDone?: (payload: { insurer: string; policyId: string }) => void;

  /** 2단계에서 policy id 목록을 불러오는 함수(없으면 기본 fetch 사용) */
  fetchPolicyIdsByInsurer?: (insurer: string) => Promise<string[]>;

  /** 1단계 보험사 목록 엔드포인트 */
  insurersEndpoint?: string;

  /** 제출 콜백(존재하면 이것이 최우선) */
  onSubmit?: (payload: { insurer: string; policyId: string }) => Promise<void>;

  /** onSubmit이 없으면 이 엔드포인트로 POST 제출 */
  submitEndpoint?: string; // e.g. "/api/user/policies/attach"
};

export default function InsurancePickerModal({
  isOpen,
  onClose,
  onDone,
  fetchPolicyIdsByInsurer,
  insurersEndpoint = "/api/policies/insurers",
  onSubmit,
  submitEndpoint = "/api/policies/attach",
}: InsurancePickerModalProps) {
  const [step, setStep] = useState<1 | 2>(1);

  // 1단계: 보험사
  const [insurers, setInsurers] = useState<string[] | null>(null);
  const [insurersError, setInsurersError] = useState<string | null>(null);
  const [insurersLoading, setInsurersLoading] = useState(false);
  const [insurerQuery, setInsurerQuery] = useState("");

  // 선택 상태
  const [selectedInsurer, setSelectedInsurer] = useState<string | null>(null);

  // 2단계: policy id
  const [policyIds, setPolicyIds] = useState<string[] | null>(null);
  const [policyIdsError, setPolicyIdsError] = useState<string | null>(null);
  const [policyIdsLoading, setPolicyIdsLoading] = useState(false);
  const [policyQuery, setPolicyQuery] = useState("");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);

  // 제출 상태
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 열릴 때 초기화 + 보험사 로드
  useEffect(() => {
    if (!isOpen) return;
    setStep(1);
    setSelectedInsurer(null);
    setPolicyIds(null);
    setPolicyIdsError(null);
    setPolicyQuery("");
    setSelectedPolicyId(null);
    setSubmitError(null);
    setSubmitting(false);

    let cancelled = false;
    (async () => {
      setInsurersLoading(true);
      setInsurersError(null);
      try {
        const res = await fetch(insurersEndpoint, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as InsurersResponse;
        if (!cancelled) setInsurers(json.insurers ?? []);
      } catch (e: any) {
        if (!cancelled) setInsurersError(e?.message || "Failed to load insurers");
      } finally {
        if (!cancelled) setInsurersLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, insurersEndpoint]);

  // 필터링
  const filteredInsurers = useMemo(() => {
    const q = insurerQuery.trim().toLowerCase();
    if (!insurers) return [];
    if (!q) return insurers;
    return insurers.filter((n) => n.toLowerCase().includes(q));
  }, [insurers, insurerQuery]);

  const filteredPolicyIds = useMemo(() => {
    const q = policyQuery.trim().toLowerCase();
    if (!policyIds) return [];
    if (!q) return policyIds;
    return policyIds.filter((id) => id.toLowerCase().includes(q));
  }, [policyIds, policyQuery]);

  // 단계 전환
  const handleChooseInsurer = async (insurer: string) => {
    setSelectedInsurer(insurer);
    setStep(2);
    setPolicyIds(null);
    setPolicyIdsError(null);
    setPolicyIdsLoading(true);
    setSelectedPolicyId(null);
    try {
      let ids: string[] = [];
      if (fetchPolicyIdsByInsurer) {
        ids = await fetchPolicyIdsByInsurer(insurer);
      } else {
        const res = await fetch(`/api/policies/${encodeURIComponent(insurer)}/list`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        ids = Array.isArray(json?.policy_ids)
          ? json.policy_ids
          : Array.isArray(json?.policies)
          ? json.policies
          : [];
      }
      setPolicyIds(ids);
    } catch (e: any) {
      setPolicyIdsError(e?.message || "Failed to load policy IDs");
    } finally {
      setPolicyIdsLoading(false);
    }
  };

  const handleBack = () => {
    if (step === 2) {
      setStep(1);
      setPolicyIds(null);
      setPolicyIdsError(null);
      setSelectedInsurer(null);
      setSelectedPolicyId(null);
      setSubmitError(null);
    }
  };

  // 리스트에서 “선택만”
  const handlePickPolicy = (policyId: string) => {
    setSelectedPolicyId((prev) => (prev === policyId ? null : policyId));
  };

  // 최종 제출
  const handleSubmit = async () => {
    if (!selectedInsurer || !selectedPolicyId) return;
    const payload = { insurer: selectedInsurer, policyId: selectedPolicyId };
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (onSubmit) {
        await onSubmit(payload);
      } else {
        // 기본 POST 제출
        const res = await fetch(submitEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const txt = await res.text().catch(() => "");
          throw new Error(`Submit failed: HTTP ${res.status}${txt ? ` - ${txt}` : ""}`);
        }
      }
      // 제출 성공 시 부모에 통지(옵션)
      onDone?.(payload);
      onClose();
    } catch (e: any) {
      setSubmitError(e?.message || "제출에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  // UI ----------------------------------------------------------------------
  const renderHeader = () => (
    <DialogHeader>
      <div className="flex items-center gap-2">
        {step === 2 && (
          <Button variant="ghost" size="icon" onClick={handleBack} className="mr-1">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        )}
        <DialogTitle className="text-xl">
          {step === 1 ? "나의 보험 추가하기" : `${selectedInsurer ?? ""}의 보험 선택`}
        </DialogTitle>
      </div>
    </DialogHeader>
  );

  const renderInsurerList = () => (
    <div className="space-y-3">
      <Input
        placeholder="보험사 검색"
        value={insurerQuery}
        onChange={(e) => setInsurerQuery(e.target.value)}
      />
      <div className="text-sm text-muted-foreground">
        총 {insurers?.length ?? 0}곳 중 {filteredInsurers.length}곳 표시
      </div>
      <ScrollArea className="h-72 rounded-md border p-2">
        {insurersLoading && (
          <div className="flex items-center justify-center py-10 text-sm">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 불러오는 중...
          </div>
        )}
        {!insurersLoading && insurersError && (
          <div className="text-sm text-destructive">{insurersError}</div>
        )}
        {!insurersLoading && !insurersError && filteredInsurers.length === 0 && (
          <div className="text-sm text-muted-foreground">검색 결과가 없습니다.</div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {filteredInsurers.map((name) => (
            <button
              key={name}
              onClick={() => handleChooseInsurer(name)}
              className="text-left rounded-2xl border p-3 hover:shadow-sm active:scale-[0.99] transition"
            >
              <div className="font-medium">{name}</div>
              <div className="text-xs text-muted-foreground">선택하려면 클릭</div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );

  const renderPolicyList = () => (
    <div className="space-y-3">
      <Input
        placeholder="증권번호/ID 검색"
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
          {filteredPolicyIds.map((pid) => {
            const selected = pid === selectedPolicyId;
            return (
              <button
                key={pid}
                onClick={() => handlePickPolicy(pid)}
                className={`flex items-center justify-between rounded-2xl border p-3 hover:shadow-sm active:scale-[0.99] transition ${
                  selected ? "ring-2 ring-primary/60 border-primary/50" : ""
                }`}
              >
                <div className="truncate mr-3">{pid}</div>
                {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              </button>
            );
          })}
        </div>
      </ScrollArea>

      {submitError && <div className="text-sm text-destructive">{submitError}</div>}

      <Separator />
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          원하는 항목이 없다면 백엔드 동기화를 확인하세요.
        </div>
        <div className="space-x-2">
          <Button variant="outline" onClick={handleBack} disabled={submitting}>
            이전
          </Button>
          <Button
            onClick={handleSubmit}
            variant="secondary"
            disabled={!selectedPolicyId || submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                제출 중...
              </>
            ) : (
              "제출"
            )}
          </Button>
        </div>
      </div>
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        {renderHeader()}
        {step === 1 ? renderInsurerList() : renderPolicyList()}
      </DialogContent>
    </Dialog>
  );
}
