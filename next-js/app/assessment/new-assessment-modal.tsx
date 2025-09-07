"use client"

import { useState, useEffect, useMemo } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Loader2, ChevronLeft, Check, Plus } from "lucide-react"

interface MyInsurance {

  id: number
  policy_id: string
  insurer: string
}

interface NewAssessmentModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete?: (assessmentId: number) => void
}

export default function NewAssessmentModal({ isOpen, onClose, onComplete }: NewAssessmentModalProps) {
  const [step, setStep] = useState<1 | 2>(1)

  // Step 1: 내 보험 선택
  const [myInsurances, setMyInsurances] = useState<MyInsurance[]>([])
  const [insurancesLoading, setInsurancesLoading] = useState(false)
  const [insurancesError, setInsurancesError] = useState<string | null>(null)
  const [insuranceQuery, setInsuranceQuery] = useState("")
  const [selectedInsurance, setSelectedInsurance] = useState<MyInsurance | null>(null)

  // Step 2: 채팅 이름 설정
  const [assessmentName, setAssessmentName] = useState("")

  // 제출 상태
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // 모달이 열릴 때 초기화 및 내 보험 리스트 로드
  useEffect(() => {
    if (!isOpen) return

    // 상태 초기화
    setStep(1)
    setSelectedInsurance(null)
    setAssessmentName("")
    setSubmitError(null)
    setSubmitting(false)
    setInsuranceQuery("")

    // 내 보험 리스트 로드 (더미 데이터)
    // setInsurancesLoading(true)
    // setInsurancesError(null)

    // 실제로는 API 호출: GET /api/me/policies (Next API 라우팅 통해 백엔드 프록시)
    ;(async () => {
      try {
        const res = await fetch('/api/me/policies', { cache: 'no-store' })
        if (!res.ok) throw new Error(`API ${res.status}`)
        const data: MyInsurance[] = await res.json()
        setMyInsurances(data)
      } catch (e) {
        setMyInsurances([])
        setInsurancesError('내 보험 정보를 불러오지 못했습니다.')
      } finally {
        setInsurancesLoading(false)
      }
    })()
  }, [isOpen])

  // 검색 필터
  const filteredInsurances = useMemo(() => {
    const q = insuranceQuery.trim().toLowerCase()
    if (!q) return myInsurances
    return myInsurances.filter(
      (insurance) =>
        insurance.insurer.toLowerCase().includes(q) || insurance.policy_id.toLowerCase().includes(q),
    )
  }, [myInsurances, insuranceQuery])

  const handleSelectInsurance = (insurance: MyInsurance) => {
    setSelectedInsurance(insurance)
    setAssessmentName(`${insurance.insurer} 심사`)
    setStep(2)
  }

  const handleBack = () => {
    if (step === 2) {
      setStep(1)
      setSubmitError(null)
    }
  }

  // 실제 생성 호출 (임시 더미 대신 사용)
  const handleSubmitReal = async () => {
    if (!selectedInsurance || !assessmentName.trim()) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const response = await fetch('/api/assessments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policy_instance_id: (selectedInsurance as any).id ?? 0,
          assessment_name: assessmentName.trim(),
        }),
      })
      if (!response.ok) throw new Error('심사 생성에 실패했습니다')
      const data = (await response.json()) as { id: number }
      onComplete?.(data.id)
      onClose()
    } catch (error: any) {
      setSubmitError(error.message || '심사 생성에 실패했습니다')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSubmit = async () => {
    if (!selectedInsurance || !assessmentName.trim()) return

    setSubmitting(true)
    setSubmitError(null)

    try {
      // 실제로는 POST /assessments API 호출
      // const response = await fetch('/assessments', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     policy_id: selectedInsurance.policy_id,
      //     assessment_name: assessmentName.trim()
      //   })
      // })
      //
      // if (!response.ok) throw new Error('심사 생성에 실패했습니다')
      // const data = await response.json() as { id: number }
      // const assessmentId = data.id

      // 더미 응답
      await new Promise((resolve) => setTimeout(resolve, 1000))
      const assessmentId = Math.floor(Math.random() * 1000) + 1

      onComplete?.(assessmentId)
      onClose()
    } catch (error: any) {
      setSubmitError(error.message || "심사 생성에 실패했습니다")
    } finally {
      setSubmitting(false)
    }
  }

  const renderHeader = () => (
    <DialogHeader>
      <div className="flex items-center gap-2">
        {step === 2 && (
          <Button variant="ghost" size="icon" onClick={handleBack} className="mr-1">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        )}
        <DialogTitle className="text-xl">{step === 1 ? "심사할 보험 선택" : "심사 이름 설정"}</DialogTitle>
      </div>
    </DialogHeader>
  )

  const renderInsuranceSelection = () => (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-gray-600 mb-3">
          심사를 진행할 보험을 선택해주세요. 선택한 보험사의 문서를 분석하고 채팅을 시작할 수 있습니다.
        </p>
        <Input
          placeholder="보험사 또는 상품명으로 검색"
          value={insuranceQuery}
          onChange={(e) => setInsuranceQuery(e.target.value)}
        />
      </div>

      <div className="text-sm text-gray-500">
        총 {myInsurances.length}건 중 {filteredInsurances.length}건 표시
      </div>

      <ScrollArea className="h-72 rounded-md border p-2">
        {insurancesLoading && (
          <div className="flex items-center justify-center py-10 text-sm">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />내 보험 정보를 불러오는 중...
          </div>
        )}

        {!insurancesLoading && insurancesError && <div className="text-sm text-red-600">{insurancesError}</div>}

        {!insurancesLoading && !insurancesError && filteredInsurances.length === 0 && (
          <div className="text-sm text-gray-500 text-center py-10">
            {insuranceQuery ? "검색 결과가 없습니다." : "등록된 보험이 없습니다."}
          </div>
        )}

        <div className="grid grid-cols-1 gap-2">
          {filteredInsurances.map((insurance) => (
            <button
              key={insurance.policy_id}
              onClick={() => handleSelectInsurance(insurance)}
              className="text-left rounded-lg border p-3 hover:shadow-md hover:border-orange-300 transition-all duration-200"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium text-gray-900 mb-1">{insurance.insurer}</div>
                  <div className="text-xs text-gray-500">ID: {insurance.policy_id}</div>
                </div>
                <Plus className="h-4 w-4 text-gray-400 mt-1" />
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  )

  const renderNameSetting = () => (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-gray-600 mb-3">
          선택한 보험:{" "}
          <span className="font-medium text-orange-600">
            {selectedInsurance?.insurer} (ID: {selectedInsurance?.policy_id})
          </span>
        </p>
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">심사 이름</label>
          <Input
            placeholder="심사 이름을 입력하세요"
            value={assessmentName}
            onChange={(e) => setAssessmentName(e.target.value)}
            className="w-full"
          />
          <p className="text-xs text-gray-500">심사 이름은 나중에 심사 목록에서 구분하기 위해 사용됩니다.</p>
        </div>
      </div>

      {submitError && <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{submitError}</div>}

      <Separator />

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={handleBack} disabled={submitting}>
          이전
        </Button>
        <Button
          onClick={handleSubmitReal}
          disabled={!assessmentName.trim() || submitting}
          className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white"
        >
          {submitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              심사 생성 중...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              심사 시작하기
            </>
          )}
        </Button>
      </div>
    </div>
  )

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        {renderHeader()}
        <div className="mt-4">{step === 1 ? renderInsuranceSelection() : renderNameSetting()}</div>
      </DialogContent>
    </Dialog>
  )
}
