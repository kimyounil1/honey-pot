"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Plus, FileText, MessageCircle, User, LogOut } from "lucide-react"
import Link from "next/link"
import NewAssessmentModal from "./new-assessment-modal"

interface Assessment {
  id: number
  title: string
  insurer: string
  created_at: string
  last_message?: string
  message_count?: number
}

interface ChatHistory {
  id: number
  title: string
  last_message?: string
  created_at: string
}

export default function AssessmentPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [showNewAssessmentModal, setShowNewAssessmentModal] = useState(false)

  // 더미 데이터 (실제로는 API에서 가져올 예정)
  useEffect(() => {
    // 심사 리스트 로드
    const dummyAssessments: Assessment[] = [
      {
        id: 1,
        title: "삼성화재 실손보험 심사",
        insurer: "삼성화재",
        created_at: "2025-01-09T10:30:00Z",
        last_message: "보험금 지급 기준에 대해 문의드립니다.",
        message_count: 5,
      },
      {
        id: 2,
        title: "현대해상 자동차보험 심사",
        insurer: "현대해상",
        created_at: "2025-01-08T15:20:00Z",
        last_message: "사고 처리 절차를 확인하고 싶습니다.",
        message_count: 3,
      },
      {
        id: 3,
        title: "KB손해보험 종합보험 심사",
        insurer: "KB손해보험",
        created_at: "2025-01-07T09:15:00Z",
        last_message: "특약 조건에 대한 질문이 있습니다.",
        message_count: 8,
      },
    ]

    // 일반 채팅 기록
    const dummyChatHistory: ChatHistory[] = [
      {
        id: 101,
        title: "보험료 절약 방법 문의",
        last_message: "월 보험료를 줄일 수 있는 방법이 있을까요?",
        created_at: "2025-01-09T14:00:00Z",
      },
      {
        id: 102,
        title: "환급금 조회",
        last_message: "놓친 환급금이 있는지 확인해주세요.",
        created_at: "2025-01-08T11:30:00Z",
      },
      {
        id: 103,
        title: "보험 가입 상담",
        last_message: "새로운 보험 가입을 고려하고 있습니다.",
        created_at: "2025-01-07T16:45:00Z",
      },
      {
        id: 104,
        title: "보장 내용 확인",
        last_message: "현재 가입한 보험의 보장 범위를 알고 싶습니다.",
        created_at: "2025-01-06T13:20:00Z",
      },
      {
        id: 105,
        title: "보험금 청구 절차",
        last_message: "보험금 청구는 어떻게 하나요?",
        created_at: "2025-01-05T10:10:00Z",
      },
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

    if (diffInHours < 24) {
      return `${diffInHours}시간 전`
    } else if (diffInHours < 24 * 7) {
      return `${Math.floor(diffInHours / 24)}일 전`
    } else {
      return date.toLocaleDateString("ko-KR")
    }
  }

  const handleLogout = async () => {
    await fetch('/api/logout', { method: 'POST' })
    window.location.href = '/'
  }

  const handleNewAssessmentComplete = (assessmentId: number) => {
    // 실제로는 새로 생성된 심사로 리다이렉트하거나 리스트를 새로고침
    console.log("새 심사 생성 완료:", assessmentId)
    // 예: router.push(`/assessment/${assessmentId}`)
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 왼쪽 사이드바 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* 헤더 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-lg flex items-center justify-center">
                <FileText className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-gray-800">꿀통</span>
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-gray-500 hover:text-gray-700">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>

          {/* 새 심사 추가 버튼 */}
          <Button
            onClick={() => setShowNewAssessmentModal(true)}
            className="w-full bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />새 심사 추가
          </Button>
        </div>

        {/* 콘텐츠 영역 */}
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-6">
            {/* 심사 리스트 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <FileText className="h-4 w-4 mr-2" />
                보험 심사 ({assessments.length})
              </h3>
              <div className="space-y-2">
                {assessments.map((assessment) => (
                  <Card
                    key={assessment.id}
                    className="cursor-pointer hover:shadow-md transition-shadow border-0 shadow-sm"
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-sm text-gray-900 line-clamp-1">{assessment.title}</h4>
                        <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                          {formatDate(assessment.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded-full">
                          {assessment.insurer}
                        </span>
                        {assessment.message_count && (
                          <span className="text-xs text-gray-500">{assessment.message_count}개 메시지</span>
                        )}
                      </div>
                      {assessment.last_message && (
                        <p className="text-xs text-gray-600 mt-2 line-clamp-2">{assessment.last_message}</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            <Separator />

            {/* 일반 채팅 기록 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                <MessageCircle className="h-4 w-4 mr-2" />
                채팅 기록
              </h3>
              <div className="space-y-2">
                {chatHistory.slice(0, 10).map((chat) => (
                  <Card key={chat.id} className="cursor-pointer hover:shadow-md transition-shadow border-0 shadow-sm">
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-sm text-gray-900 line-clamp-1">{chat.title}</h4>
                        <span className="text-xs text-gray-500 ml-2 flex-shrink-0">{formatDate(chat.created_at)}</span>
                      </div>
                      {chat.last_message && <p className="text-xs text-gray-600 line-clamp-2">{chat.last_message}</p>}
                    </CardContent>
                  </Card>
                ))}

                {chatHistory.length > 10 && (
                  <div className="text-center py-2">
                    <Button variant="ghost" size="sm" className="text-gray-500">
                      더 보기 ({chatHistory.length - 10}개 더)
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>

        {/* 하단 사용자 정보 */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
              <User className="h-4 w-4 text-gray-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">사용자</p>
              <p className="text-xs text-gray-500">user@example.com</p>
            </div>
          </div>
        </div>
      </div>

      {/* 오른쪽 메인 영역 */}
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center mx-auto">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">보험 심사 분석</h2>
            <p className="text-gray-600 max-w-md">
              새로운 심사를 시작하거나 기존 심사를 선택하여 보험 관련 문서를 분석하고 채팅을 시작하세요.
            </p>
          </div>
          <Button
            onClick={() => setShowNewAssessmentModal(true)}
            className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />새 심사 시작하기
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
