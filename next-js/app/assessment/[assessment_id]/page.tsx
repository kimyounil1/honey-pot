"use client"

import { useRouter, useParams } from "next/navigation"
import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ArrowLeft, Send, Paperclip, FileText, User, Bot, Upload } from "lucide-react"
import Link from "next/link"
import FileUploadPanel from "./file-upload-panel"

interface AssessmentInfo {
  id: number
  title: string
  insurer: string
  created_at: string
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  attachment?: {
    filename?: string
    file_type?: string
  }
}

type NonDoneState = "commencing" | "classifying" | "analyzing" | "searching" | "building" | "failed"
type MessageState = NonDoneState | "done" | "complete"
const TERMINAL_STATES: MessageState[] = ["done", "failed", "complete"]
const isTerminal = (s: MessageState) => TERMINAL_STATES.includes(s)

type BannerType = "info" | "success" | "error" | "loading"
function TopBanner({
  open,
  text,
  type = "info",
}: {
  open: boolean
  text: string
  type?: BannerType
}) {
  if (!open) return null
  const base =
    "fixed top-4 left-1/2 -translate-x-1/2 z-50 " +
    "max-w-md w-[calc(100%-2rem)] px-4 py-2 rounded-xl shadow-lg " +
    "backdrop-blur-lg ring-1 ring-white/10 " +
    "transition-all duration-300 ease-out animate-in fade-in slide-in-from-top-2"
  const color =
    type === "success"
      ? "bg-emerald-600/60 text-white"
      : type === "error"
        ? "bg-red-600/60 text-white"
        : type === "loading"
          ? "bg-sky-600/60 text-white"
          : "bg-slate-800/60 text-white"

  return (
    <div className={`${base} ${color}`} role="status" aria-live="polite" style={{ pointerEvents: "auto" }}>
      <div className="flex items-center gap-2 text-sm font-medium">
        {type === "success" && <span aria-hidden className="i-lucide:check-circle-2 size-4" />}
        {type === "error" && <span aria-hidden className="i-lucide:triangle-alert size-4" />}
        {type === "loading" && <span aria-hidden className="i-lucide:loader-2 size-4 animate-spin" />}
        <span className="truncate">{text}</span>
      </div>
    </div>
  )
}

export default function AssessmentChatPage() {
  const router = useRouter()
  const params = useParams()
  const assessmentId = params?.assessment_id as string

  // 심사 정보
  const [assessmentInfo, setAssessmentInfo] = useState<AssessmentInfo | null>(null)
  const [assessmentLoading, setAssessmentLoading] = useState(true)

  // 메시지 관련 상태
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messageState, setMessageState] = useState<MessageState>()

  // UI 상태
  const [showFilePanel, setShowFilePanel] = useState(false)

  // 배너 표시
  const [bannerOpen, setBannerOpen] = useState(false)
  const [bannerText, setBannerText] = useState("")
  const [bannerType, setBannerType] = useState<BannerType>("info")

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const STATE_TEXT: Record<NonDoneState, string> = {
    commencing: "...",
    classifying: "메세지를 분류중입니다...",
    analyzing: "제공하신 자료를 분석중입니다...",
    searching: "데이터를 바탕으로 결과를 분석중입니다...",
    building: "응답을 받아오는 중...",
    failed: "에러 발생",
  }

  function showBanner(text: string, type: BannerType = "info") {
    setBannerText(text)
    setBannerType(type)
    setBannerOpen(true)
  }

  function hideBanner() {
    setBannerOpen(false)
  }

  // 심사 정보 로드
  useEffect(() => {
    if (!assessmentId) return

    const fetchAssessmentInfo = async () => {
      try {
        // 실제로는 GET /assessments/{assessment_id} API 호출
        // const response = await fetch(`/api/assessments/${assessmentId}`)
        // const data = await response.json()

        // 더미 데이터
        const dummyInfo: AssessmentInfo = {
          id: Number.parseInt(assessmentId),
          title: "삼성화재 실손보험 심사",
          insurer: "삼성화재",
          created_at: "2025-01-09T10:30:00Z",
        }

        setAssessmentInfo(dummyInfo)
      } catch (error) {
        console.error("심사 정보 로드 실패:", error)
      } finally {
        setAssessmentLoading(false)
      }
    }

    fetchAssessmentInfo()
  }, [assessmentId])

  // 메시지 히스토리 로드
  const fetchMessageHistory = async () => {
    if (!assessmentId) return

    try {
      // 실제로는 GET /assessments/{assessment_id}/messages API 호출
      // const response = await fetch(`/api/assessments/${assessmentId}/messages`)
      // const data = await response.json()

      // 더미 메시지 데이터
      const dummyMessages: Message[] = [
        {
          id: "1",
          role: "assistant",
          content:
            "안녕하세요! 삼성화재 실손보험 심사를 시작하겠습니다. 궁금한 점이나 분석하고 싶은 내용을 말씀해 주세요.",
          timestamp: "2025-01-09T10:30:00Z",
        },
        {
          id: "2",
          role: "user",
          content: "보험금 지급 기준에 대해 문의드립니다.",
          timestamp: "2025-01-09T10:31:00Z",
        },
        {
          id: "3",
          role: "assistant",
          content:
            "삼성화재 실손보험의 보험금 지급 기준에 대해 설명드리겠습니다. 실손보험은 실제 의료비 지출액에서 본인부담금을 제외한 금액을 보장합니다...",
          timestamp: "2025-01-09T10:32:00Z",
        },
      ]

      setMessages(dummyMessages)
    } catch (error) {
      console.error("메시지 히스토리 로드 실패:", error)
    }
  }

  useEffect(() => {
    fetchMessageHistory()
  }, [assessmentId])

  // 메시지 상태 폴링
  useEffect(() => {
    if (!assessmentId) return

    let active = true
    let timeoutId: number | undefined
    const controller = new AbortController()

    const tick = async () => {
      if (!active) return

      try {
        // 실제로는 GET /assessments/{assessment_id}/messageState API 호출
        const res = await fetch(`/api/assessments/${assessmentId}/messageState?t=${Date.now()}`, {
          cache: "no-store",
          headers: { "Cache-Control": "no-cache" },
          signal: controller.signal,
        })
        if (!res.ok) throw new Error(`API Error: ${res.status}`)
        const data = await res.json()
        const state = data.state as MessageState

        setMessageState(state)

        if (isTerminal(state)) {
          await fetchMessageHistory()
          active = false
          return
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          console.error(e)
        }
      }

      if (active) {
        timeoutId = window.setTimeout(tick, 300)
      }
    }

    return () => {
      active = false
      if (timeoutId) clearTimeout(timeoutId)
      controller.abort()
    }
  }, [assessmentId])

  // 메시지 전송
  const handleSendMessage = async () => {
    if (!input.trim() || isLoading || !assessmentId) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // 실제로는 POST /assessments/{assessment_id}/messages API 호출
      // const response = await fetch(`/api/assessments/${assessmentId}/messages`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ content: input.trim() })
      // })

      // 더미 응답
      setTimeout(() => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "메시지를 받았습니다. 분석 중입니다...",
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMessage])
        setIsLoading(false)
      }, 1000)
    } catch (error) {
      console.error("메시지 전송 실패:", error)
      setIsLoading(false)
      showBanner("메시지 전송에 실패했습니다.", "error")
    }
  }

  // 파일 업로드 완료 처리
  const handleFileUploaded = () => {
    showBanner("파일이 업로드되고 OCR 처리가 완료되었습니다.", "success")
  }

  // 메시지 끝으로 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  if (assessmentLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">심사 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <TopBanner open={bannerOpen} text={bannerText} type={bannerType} />

      {/* 메인 채팅 영역 */}
      <div className={`flex flex-col transition-all duration-300 ${showFilePanel ? "w-2/3" : "w-full"}`}>
        {/* 헤더 */}
        <div className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Link href="/assessment">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  심사 목록
                </Button>
              </Link>
              <div className="h-6 w-px bg-gray-300" />
              <div>
                <h1 className="font-semibold text-gray-900">{assessmentInfo?.title}</h1>
                <p className="text-sm text-orange-600">{assessmentInfo?.insurer}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilePanel(!showFilePanel)}
                className={showFilePanel ? "bg-orange-50 text-orange-600" : ""}
              >
                <Upload className="h-4 w-4 mr-2" />
                첨부파일
              </Button>
              <span className="text-xs text-gray-500">심사 ID: {assessmentId}</span>
            </div>
          </div>
        </div>

        {/* 메시지 영역 */}
        <ScrollArea className="flex-1 p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`flex items-start space-x-3 max-w-3xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${message.role === "user" ? "bg-orange-500" : "bg-gray-200"}`}
                  >
                    {message.role === "user" ? (
                      <User className="h-4 w-4 text-white" />
                    ) : (
                      <Bot className="h-4 w-4 text-gray-600" />
                    )}
                  </div>
                  <Card className={`${message.role === "user" ? "bg-orange-500 text-white" : "bg-white"}`}>
                    <CardContent className="p-3">
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      {message.attachment && (
                        <div className="mt-2 p-2 bg-gray-100 rounded text-xs text-gray-600">
                          <FileText className="h-3 w-3 inline mr-1" />
                          {message.attachment.filename}
                        </div>
                      )}
                      <p className={`text-xs mt-2 ${message.role === "user" ? "text-orange-100" : "text-gray-500"}`}>
                        {new Date(message.timestamp).toLocaleTimeString("ko-KR")}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            ))}

            {/* 로딩 상태 표시 */}
            {(isLoading || (messageState && !isTerminal(messageState))) && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-3 max-w-3xl">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-gray-600" />
                  </div>
                  <Card className="bg-white">
                    <CardContent className="p-3">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-500"></div>
                        <p className="text-sm text-gray-600">
                          {messageState ? STATE_TEXT[messageState as NonDoneState] || "처리 중..." : "응답 중..."}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* 입력 영역 */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilePanel(!showFilePanel)}
                className="flex-shrink-0"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <div className="flex-1">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
                  placeholder="메시지를 입력하세요..."
                  disabled={isLoading}
                  className="resize-none"
                />
              </div>
              <Button
                onClick={handleSendMessage}
                disabled={!input.trim() || isLoading}
                className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white flex-shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 파일 업로드 패널 */}
      {showFilePanel && (
        <div className="w-1/3 border-l border-gray-200 bg-white p-4">
          <FileUploadPanel assessmentId={assessmentId} onFileUploaded={handleFileUploaded} />
        </div>
      )}
    </div>
  )
}
