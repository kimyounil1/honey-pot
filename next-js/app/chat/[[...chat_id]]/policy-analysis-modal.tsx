"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { FileText } from 'lucide-react'
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Loader2, Plus, Check } from "lucide-react";

// --- Types -----------------------------------------------------------------
export type InsurersResponse = { insurers: string[] };

export type PolicyAnalysisModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onDone?: (payload: { policy_id: string }) => void;
  fetchPolicyIdsByInsurer?: (insurer: string) => Promise<string[]>;
  insurersEndpoint?: string;
  submitEndpoint?: string;
}


export default function PolicyAnalysisModal({ 
  isOpen, onClose,onDone,
  fetchPolicyIdsByInsurer,
  insurersEndpoint = "/api/policies/insurers",
  // onAnalyze 
}: PolicyAnalysisModalProps) {
  // states -----------------------------------------------------------
  const [step, setStep] = useState<1 | 2>(1);
    // Insurer list
  const [insurers, setInsurers] = useState<string[] | null>(null);
  const [insurersError, setInsurersError] = useState<string | null>(null);
  const [insurersLoading, setInsurersLoading] = useState(false);
  const [insurerQuery, setInsurerQuery] = useState("");  // Selection state
  const [selectedInsurer, setSelectedInsurer] = useState<string | null>(null);
    // Policy IDs by chosen insurer
  const [policyIds, setPolicyIds] = useState<string[] | null>(null);
  const [policyIdsError, setPolicyIdsError] = useState<string | null>(null);
  const [policyIdsLoading, setPolicyIdsLoading] = useState(false);
  const [policyQuery, setPolicyQuery] = useState("");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
    // submitting from list state
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

// functions -----------------------------------------------------------
  // ########## 리스트에서 선택하는 부분 함수들 ##########
    // Reset internal state whenever the dialog opens
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

    // fetch insurers on open
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

    // Filtered views
  const filteredInsurers = useMemo(() => {
    const q = insurerQuery.trim().toLowerCase();
    if (!insurers) return [] as string[];
    if (!q) return insurers;
    return insurers.filter((n) => n.toLowerCase().includes(q));
  }, [insurers, insurerQuery]);

  const filteredPolicyIds = useMemo(() => {
    const q = policyQuery.trim().toLowerCase();
    if (!policyIds) return [] as string[];
    if (!q) return policyIds;
    return policyIds.filter((id) => id.toLowerCase().includes(q));
  }, [policyIds, policyQuery]);
  
    // Step transitions
  const handleChooseInsurer = async (insurer: string) => {
    setSelectedInsurer(insurer);
    setStep(2);
    // Load policy IDs for the chosen insurer
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
        const json = await res.json()
        ids = Array.isArray(json?.policy_ids) 
          ? json.policy_ids : Array.isArray(json?.policies) 
          ? json.policies : [];
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

  const handlePickPolicy = (policyId: string) => {
    setSelectedPolicyId((prev) => (prev === policyId ? null : policyId));
  };

  const handleAnalyze = async () => {
    if ( !selectedPolicyId ) return;
    const payload = { policy_id: selectedPolicyId }
    setSubmitting(true)
    setSubmitError(null)
    onDone?.(payload);
    onClose();
  }

// Render helpers -----------------------------------------------------------
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
          {Array.from(new Set((filteredInsurers ?? []).map(String))).map((name) => (
            <button key={name} onClick={() => handleChooseInsurer(name)} className="text-left rounded-2xl border p-3 hover:shadow-sm active:scale-[0.99] transition">
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
        <div className="space-x-2 justify" >
          <Button variant="outline" onClick={handleBack} disabled={submitting}>
            이전
          </Button>
        </div>
      </div>
    </div>
  );  

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">보험 약관 분석</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          {/* 보험 약관을 선택해서 진행하는 부분 */}
          {step === 1 ? renderInsurerList() : renderPolicyList()}

          <div className="relative">
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">
                ⚠️ 직접 약관파일을 첨부하시는 경우, 채팅창에서 파일을 업로드 후 질문내용을 입력해주세요.
              </span>
            </div>
          </div>
        </div>
            <Button
              onClick={handleAnalyze}
              disabled={ !selectedPolicyId || submitting }
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
            >
              <FileText className="mr-2 h-4 w-4" />약관분석 시작하기
            </Button>
      </DialogContent>
    </Dialog>
  )
}
