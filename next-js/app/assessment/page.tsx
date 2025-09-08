"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { FileText, Plus } from "lucide-react"
import AssessmentSidebar, { AssessmentItem as Assessment, ChatHistoryItem as ChatHistory } from "@/components/AssessmentSidebar"
import NewAssessmentModal from "./new-assessment-modal"

export default function AssessmentPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [showNewAssessmentModal, setShowNewAssessmentModal] = useState(false)

  useEffect(() => {
    const dummyAssessments: Assessment[] = [
      { id: 1, title: "자동차보험 보상 문의", insurer: "롯데손해보험", created_at: "2025-01-09T10:30:00Z", last_message: "합의금 적정성 확인", message_count: 5 },
      { id: 2, title: "추돌사고 휴업손해 문의", insurer: "현대해상", created_at: "2025-01-08T15:20:00Z", last_message: "휴업손해 반영 가능성 문의", message_count: 4 },
      { id: 3, title: "렌트카 비용 보상 문의", insurer: "삼성화재", created_at: "2025-01-07T09:15:00Z", last_message: "대차 기간 인정 범위 확인", message_count: 6 },
    ]
    const dummyChatHistory: ChatHistory[] = [
      { id: 101, title: "보험 가입 문의", last_message: "계약 추천 부탁드려요.", created_at: "2025-01-09T14:00:00Z" },
      { id: 102, title: "보상 진행 조회", last_message: "진행 상황 확인", created_at: "2025-01-08T11:30:00Z" },
      { id: 103, title: "보험 가이드 상담", last_message: "갱신 안내", created_at: "2025-01-07T16:45:00Z" },
      { id: 104, title: "보장 내용 확인", last_message: "보장 범위 문의", created_at: "2025-01-06T13:20:00Z" },
      { id: 105, title: "추가 절차 안내", last_message: "절차 개요 설명", created_at: "2025-01-05T10:10:00Z" },
    ]

    ;(async () => {
      try {
        const res = await fetch('/api/assessments', { cache: 'no-store' })
        if (res.ok) {
          const real: Assessment[] = await res.json()
          const merged = [...real, ...dummyAssessments]
          const seen = new Set<number>()
          const unique = merged.filter((a) => (seen.has(a.id) ? false : (seen.add(a.id), true)))
          setAssessments(unique)
        } else {
          setAssessments(dummyAssessments)
        }
      } catch {
        setAssessments(dummyAssessments)
      } finally {
        setChatHistory(dummyChatHistory)
        setLoading(false)
      }
    })()
  }, [])

  const handleLogout = async () => {
    await fetch('/api/logout', { method: 'POST' })
    window.location.href = '/'
  }

  const handleNewAssessmentComplete = (assessmentId: number) => {
    console.log('문서 분석 생성 완료:', assessmentId)
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <AssessmentSidebar
        assessments={assessments}
        chatHistory={chatHistory}
        onNewAssessmentClick={() => setShowNewAssessmentModal(true)}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center mx-auto">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">보험 서류 분석</h2>
            <p className="text-gray-600 max-w-md mx-auto">
              새로 분석을 생성하거나 기존 분석을 선택해 문서를 업로드하고 결과를 확인하세요.
            </p>
          </div>
          <Button onClick={() => setShowNewAssessmentModal(true)} className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white">
            <Plus className="h-4 w-4 mr-2" />문서 분석 시작
          </Button>
        </div>
      </div>

      <NewAssessmentModal
        isOpen={showNewAssessmentModal}
        onClose={() => setShowNewAssessmentModal(false)}
        onComplete={handleNewAssessmentComplete}
      />
    </div>
  )
}
