"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Plus, FileText, MessageCircle, User, LogOut } from "lucide-react"

export type AssessmentItem = {
  id: number
  title: string
  insurer: string
  created_at: string
  last_message?: string
  message_count?: number
}

export type ChatHistoryItem = {
  id: number
  title: string
  last_message?: string
  created_at: string
}

export default function AssessmentSidebar({
  assessments,
  chatHistory,
  onNewAssessmentClick,
  onLogout,
}: {
  assessments: AssessmentItem[]
  chatHistory: ChatHistoryItem[]
  onNewAssessmentClick: () => void
  onLogout: () => void
}) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    if (diffInHours < 24) return `${diffInHours}시간 전`
    if (diffInHours < 24 * 7) return `${Math.floor(diffInHours / 24)}일 전`
    return date.toLocaleDateString("ko-KR")
  }

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-orange-400 to-orange-500 rounded-lg flex items-center justify-center">
              <FileText className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-gray-800">꿀통</span>
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={onLogout}
            className="text-gray-500 hover:text-gray-700"
            aria-label="로그아웃"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>

        <Button
          onClick={onNewAssessmentClick}
          className="w-full bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white"
        >
          <Plus className="h-4 w-4 mr-2" />새 분석
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
              <FileText className="h-4 w-4 mr-2" />
              보험 분석 ({assessments.length})
            </h3>
            <div className="space-y-2">
              {assessments.map((assessment) => (
                <Link key={assessment.id} href={`/assessment/${assessment.id}`}>
                  <Card className="cursor-pointer hover:shadow-md transition-shadow border-0 shadow-sm">
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
                        {typeof assessment.message_count === 'number' && (
                          <span className="text-xs text-gray-500">{assessment.message_count}개 메시지</span>
                        )}
                      </div>
                      {assessment.last_message && (
                        <p className="text-xs text-gray-600 mt-2 line-clamp-2">{assessment.last_message}</p>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
          <Separator />
        </div>
      </ScrollArea>

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
  )
}

