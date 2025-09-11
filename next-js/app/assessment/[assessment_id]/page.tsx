"use client"

import { useParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Upload, Send, Menu } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import AssessmentSidebar, { AssessmentItem, ChatHistoryItem } from "@/components/AssessmentSidebar"

type Message = {
  id: number
  role: "user" | "assistant"
  content: string
  timestamp: string
}

type MessageState = "commencing" | "classifying" | "analyzing" | "searching" | "building" | "done" | "failed" | "complete"

type UploadItem = {
  upload_id: string
  filename: string
  file_type?: string | null
  file_size?: number | null
  upload_status: string
  ocr_status?: string | null
  created_at: string
}

export default function AssessmentRoomPage() {
  const params = useParams()
  const assessmentId = Number((params as any)?.assessment_id)
  // Demo for three samples (id: 1, 2, 3)
  const isDemo = assessmentId === 1 || assessmentId === 2 || assessmentId === 3

  // Sidebar data
  const [assessments, setAssessments] = useState<AssessmentItem[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([])
  useEffect(() => {
    const dummyAssessments: AssessmentItem[] = [
      { id: 1, title: "자동차보험 보상 문의", insurer: "롯데손해보험", created_at: new Date().toISOString(), last_message: "최근 메시지", message_count: 5 },
      { id: 2, title: "추돌사고 휴업손해 문의", insurer: "현대해상", created_at: new Date(Date.now() - 86400000).toISOString(), last_message: "휴업손해 반영 가능성 문의", message_count: 4 },
      { id: 3, title: "렌트카 비용 보상 문의", insurer: "삼성화재", created_at: new Date(Date.now() - 86400000 * 2).toISOString(), last_message: "대차 기간 인정 범위 확인", message_count: 6 },
    ]
    const dummyChatHistory: ChatHistoryItem[] = [
      { id: 101, title: "채팅 기록 1", created_at: new Date().toISOString() },
      { id: 102, title: "채팅 기록 2", created_at: new Date(Date.now() - 3600000).toISOString() },
    ]
    ;(async () => {
      try {
        const r = await fetch('/api/assessments', { cache: 'no-store' })
        if (r.ok) {
          const real: AssessmentItem[] = await r.json()
          const seen = new Set<number>()
          const merged = [...real, ...dummyAssessments].filter(a => seen.has(a.id) ? false : (seen.add(a.id), true))
          setAssessments(merged)
        } else {
          setAssessments(dummyAssessments)
        }
      } catch {
        setAssessments(dummyAssessments)
      } finally {
        setChatHistory(dummyChatHistory)
      }
    })()
  }, [])

  const handleLogout = async () => {
    await fetch('/api/logout', { method: 'POST' })
    window.location.href = '/'
  }

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [state, setState] = useState<MessageState | undefined>()
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [sending, setSending] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const bottomRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const fetchMessages = async () => {
    if (!assessmentId) return
    if (isDemo) {
      const now = new Date()
      if (assessmentId === 1) {
        setMessages([
          { id: 1, role: 'user', content: '자동차보험 보상 문의드립니다. 합의금이 적정한지 봐주세요.', timestamp: new Date(now.getTime() - 1000 * 60 * 22).toISOString() },
          { id: 2, role: 'assistant', content: '첨부된 카톡 대화와 심사 내역서를 확인했어요. 초기 제시액에는 위자료와 휴업손해 일부가 반영되지 않았습니다. 몇 가지 보완 시 추가 수령 가능성이 있습니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 20).toISOString() },
          { id: 3, role: 'assistant', content: '예상 추가 수령 범위는 약 35만~60만원입니다. 세부 근거는 아래와 같아요:\n- 위자료: 경미 상해 기준 가이드 상향 여지\n- 교통비/치료비 누락분\n- 휴업손해: 소득 증빙 시 부분 반영 가능', timestamp: new Date(now.getTime() - 1000 * 60 * 18).toISOString() },
          { id: 4, role: 'user', content: '그러면 뭐 어떻게 해야하나요?', timestamp: new Date(now.getTime() - 1000 * 60 * 16).toISOString() },
          { id: 5, role: 'assistant', content: '진행 방법 안내드릴게요.\n\n요약 금액(가정):\n- 총 손해 추정액: 1,800,000원\n- 현재 제시액: 1,250,000원\n- 추가 수령 예상: 350,000~600,000원\n- 목표 합계: 1,600,000~1,850,000원\n\n다음 순서로 진행해 주세요:\n1) 치료비/약제비/교통비 영수증 재정리 후 스캔 업로드\n2) 소득증빙(재직·급여명세 등) 제출 → 휴업손해 반영 요청\n3) 위자료 상향 사유(통원빈도/통증/불편사항) 메모 정리\n4) 위 내용 근거로 조정요청서 또는 담당자에게 카톡/메일 발송\n\n필요하시면 제가 제출용 문구도 정리해 드릴게요.', timestamp: new Date(now.getTime() - 1000 * 60 * 15).toISOString() },
        ])
      } else if (assessmentId === 2) {
        setMessages([
          { id: 1, role: 'user', content: '추돌사고로 통원치료 중입니다. 휴업손해 반영이 가능한가요?', timestamp: new Date(now.getTime() - 1000 * 60 * 30).toISOString() },
          { id: 2, role: 'assistant', content: '업로드하신 통원 영수증과 진료확인서를 확인했습니다. 통원일수 및 통증 정도로 보아 단기간의 휴업손해 반영 여지가 있습니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 28).toISOString() },
          { id: 3, role: 'assistant', content: '다만 현 제시액에는 교통비 일부와 약제비 누락이 있어 보입니다. 보완 시 약 15만~30만원 증액 여지가 있습니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 26).toISOString() },
          { id: 4, role: 'user', content: '필요한 증빙은 뭐가 있을까요?', timestamp: new Date(now.getTime() - 1000 * 60 * 24).toISOString() },
          { id: 5, role: 'assistant', content: '필요 서류 안내드립니다.\n\n- 통원 영수증(교통비 포함) 원본 또는 스캔\n- 진료확인서(통원횟수/기간 확인 가능)\n- 재직증명서 + 급여명세(휴업손해 반영용)\n\n제출 후 제가 반영 요청 문구까지 정리해 드릴게요.', timestamp: new Date(now.getTime() - 1000 * 60 * 23).toISOString() },
        ])
      } else if (assessmentId === 3) {
        setMessages([
          { id: 1, role: 'user', content: '사고나서 렌트카를 사용했는데 대차 기간 인정이 애매합니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 40).toISOString() },
          { id: 2, role: 'assistant', content: '업로드하신 수리견적서와 렌트 영수증을 확인했습니다. 수리기간 대비 대차 기간 산정이 가능해 보이며 일부 불인정 기간 조정이 필요합니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 38).toISOString() },
          { id: 3, role: 'assistant', content: '현재 제시액에서는 렌트 단가가 약관 기준보다 낮게 반영된 부분이 있습니다. 단가 재산정과 필요기간 입증 시 증액 가능성이 있습니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 36).toISOString() },
          { id: 4, role: 'user', content: '그럼 어떻게 진행하면 좋을까요?', timestamp: new Date(now.getTime() - 1000 * 60 * 34).toISOString() },
          { id: 5, role: 'assistant', content: '진행 방법은 다음과 같습니다.\n\n1) 정비소 수리완료 확인서(입·출고일 포함) 요청\n2) 렌트 이용 내역서에 차량급, 단가, 일수 명시 요청\n3) 약관상 대차 인정 기준 근거 정리 후 재산정 요청\n\n이후 필요 시 담당자에게 보낼 문구도 만들어 드릴게요.', timestamp: new Date(now.getTime() - 1000 * 60 * 33).toISOString() },
        ])
      }
      return
    }
    const r = await fetch(`/api/assessments/${assessmentId}/messages`, { cache: "no-store" })
    if (r.ok) setMessages(await r.json())
  }
  const fetchUploads = async () => {
    if (!assessmentId) return
    if (isDemo) {
      const now = new Date()
      if (assessmentId === 1) {
        setUploads([
          { upload_id: 'demo-1-kt', filename: '카톡대화.txt', file_type: 'text/plain', file_size: 12456, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 30).toISOString() },
          { upload_id: 'demo-1-img', filename: '심사내역서.png', file_type: 'image/png', file_size: 342399, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 28).toISOString() },
        ])
      } else if (assessmentId === 2) {
        setUploads([
          { upload_id: 'demo-2-receipt', filename: '통원영수증.pdf', file_type: 'application/pdf', file_size: 52344, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 45).toISOString() },
          { upload_id: 'demo-2-med', filename: '진료확인서.jpg', file_type: 'image/jpeg', file_size: 234455, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 43).toISOString() },
        ])
      } else if (assessmentId === 3) {
        setUploads([
          { upload_id: 'demo-3-rent', filename: '렌트영수증.pdf', file_type: 'application/pdf', file_size: 78901, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 55).toISOString() },
          { upload_id: 'demo-3-estimate', filename: '수리견적서.png', file_type: 'image/png', file_size: 444321, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 52).toISOString() },
        ])
      }
      return
    }
    const r = await fetch(`/api/assessments/${assessmentId}/uploads`, { cache: "no-store" })
    if (r.ok) {
      const data = await r.json()
      setUploads(data.uploads || [])
    }
  }

  useEffect(() => {
    if (!assessmentId) return
    fetchMessages(); fetchUploads()
  }, [assessmentId])

  // poll assistant message state while sending
  useEffect(() => {
    if (!sending || !assessmentId || isDemo) return
    let active = true
    const tick = async () => {
      if (!active) return
      const r = await fetch(`/api/assessments/${assessmentId}/messageState`, { cache: "no-store" })
      if (r.ok) {
        const data = await r.json()
        setState(data.state as MessageState)
        if (["done", "failed", "complete"].includes(data.state)) {
          active = false
          await fetchMessages()
          setSending(false)
        } else {
          setTimeout(tick, 800)
        }
      } else {
        setTimeout(tick, 1000)
      }
    }
    tick()
    return () => { active = false }
  }, [sending, assessmentId])

  // poll uploads while OCR is in progress
  useEffect(() => {
    if (!assessmentId || isDemo) return
    const inProgress = uploads.some(u => {
      const s = (u.ocr_status || '').toLowerCase()
      return s === 'pending' || s === 'processing'
    })
    if (!inProgress) return
    let active = true
    const tick = async () => {
      if (!active) return
      try { await fetchUploads() } finally { if (active) setTimeout(tick, 1500) }
    }
    tick()
    return () => { active = false }
  }, [uploads, assessmentId])

  const onSend = async () => {
    if (!input.trim() || !assessmentId) return
    const content = input
    setInput("")
    setMessages((prev) => [...prev, { id: Date.now(), role: "user", content, timestamp: new Date().toISOString() }])
    if (isDemo) {
      // Simulate assistant answer using demo files
      setTimeout(() => {
        const lower = content.toLowerCase()
        const asksHow = content.includes('어떻게') || content.includes('어떡') || content.includes('하면 되')
        const reply = asksHow
          ? `진행 방법 안내드릴게요.\n\n요약 금액(가정):\n- 총 손해 추정액: 1,800,000원\n- 현재 제시액: 1,250,000원\n- 추가 수령 예상: 350,000~600,000원\n- 목표 합계: 1,600,000~1,850,000원\n\n다음 순서로 진행해 주세요:\n1) 치료비/약제비/교통비 영수증 재정리 후 스캔 업로드\n2) 소득증빙(재직·급여명세 등) 제출 → 휴업손해 반영 요청\n3) 위자료 상향 사유(통원빈도/통증/불편사항) 메모 정리\n4) 위 내용 근거로 조정요청서 또는 담당자에게 카톡/메일 발송\n\n필요하시면 제출용 문구도 정리해 드릴게요.`
          : `제공하신 자료(카톡 대화/심사 내역서)를 기준으로 판단해보면, 추가 수령 가능성이 있습니다.\n\n요약:\n- 초기 제시액에 위자료/교통비 누락 소지\n- 휴업손해는 소득 증빙 시 일부 반영 가능\n\n권장 대응:\n1) 병원 진료확인서 및 영수증 재정리\n2) 교통비/약제비 영수증 묶음 제출\n3) 소득 증빙(재직/급여명세)로 휴업손해 보완\n\n추정 추가 수령 범위: 약 35만~60만원\n참고로 현재 제시액 1,250,000원 기준, 목표 합계는 1,600,000~1,850,000원 수준입니다.`
        setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content: reply, timestamp: new Date().toISOString() }])
      }, 600)
      return
    }
    setSending(true)
    const r = await fetch(`/api/assessments/${assessmentId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    })
    // If post fails, revert sending flag and inform user minimally
    if (!r.ok) {
      setSending(false)
    }
  }

  const onUpload = async () => {
    if (!file || !assessmentId) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append("file", file)
      const r = await fetch(`/api/assessments/${assessmentId}/upload`, { method: "POST", body: fd })
      if (r.ok) {
        await fetchUploads()
      }
    } finally {
      setUploading(false)
      setFile(null)
      const el = document.getElementById("file-input") as HTMLInputElement | null
      if (el) el.value = ""
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar: responsive like chat page */}
      <div
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-50 w-96 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 flex flex-col lg:h-svh overflow-hidden min-h-0 flex-shrink-0`}
      >
        <AssessmentSidebar
          assessments={assessments}
          chatHistory={chatHistory}
          onNewAssessmentClick={() => { /* open modal if needed */ }}
          onLogout={handleLogout}
          onCloseMobile={() => setSidebarOpen(false)}
        />
      </div>

      {/* center: messages */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu className="h-4 w-4" />
            </Button>
            <div className="text-sm text-gray-600">분석 #{assessmentId}</div>
          </div>
        </header>
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-3">
            {/* guide chat should always appear at top */}
            <div className="flex justify-start">
              <Card className="bg-white max-w-[80%] border-dashed">
                <CardContent className="p-3 text-sm whitespace-pre-wrap">
                  안녕하세요! 보험 심사 분석을 시작할까요?
                  {"\n"}궁금한 점을 적어주시거나 문서를 업로드해 주세요.
                  {"\n"}업로드 한 파일 내용을 기반으로 분석을 진행 합니다.
                  {"\n\n"}- 대화 내용과 증빙 파일(진단서, 진료내역 등)을 첨부해 주세요.
                  {"\n"}- OCR 처리 중에는 분석이 지연될 수 있어요.
                </CardContent>
              </Card>
            </div>
            {messages.map(m => (
              <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <Card className={m.role === 'user' ? 'bg-orange-50 max-w-[80%]' : 'bg-white max-w-[80%]'}>
                  <CardContent className="p-3 text-sm">
                    {m.role === 'assistant' ? (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          ul: ({ node, ...props }) => (
                            <ul className="list-disc pl-5 my-2" {...props} />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol className="list-decimal pl-5 my-2" {...props} />
                          ),
                          li: ({ node, ...props }) => <li className="my-1" {...props} />,
                          p: ({ node, ...props }) => (
                            <p className="mb-2 whitespace-pre-wrap" {...props} />
                          ),
                          code: ({ inline, className, children, ...props }) => (
                            <code
                              className={
                                (className || "") +
                                (inline
                                  ? " px-1 py-0.5 rounded bg-slate-100"
                                  : " block w-full whitespace-pre overflow-x-auto p-2 rounded bg-slate-100")
                              }
                              {...props}
                            >
                              {children}
                            </code>
                          ),
                          a: ({ node, ...props }) => (
                            <a className="text-blue-600 underline" {...props} />
                          ),
                          table: ({ node, ...props }) => (
                            <table className="my-2 border-collapse table-auto w-full text-sm" {...props} />
                          ),
                          th: ({ node, ...props }) => (
                            <th className="border px-2 py-1 text-left bg-slate-50" {...props} />
                          ),
                          td: ({ node, ...props }) => (
                            <td className="border px-2 py-1" {...props} />
                          ),
                        }}
                      >
                        {m.content}
                      </ReactMarkdown>
                    ) : (
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ))}
            {sending && (
              <div className="text-xs text-gray-500">{state || 'commencing'}...</div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
        <div className="p-3 border-t flex gap-2">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="궁금한 점이나 분석 요청을 입력해 주세요"
            onKeyDown={e => { if (e.key === 'Enter') onSend() }}
          />
          <Button onClick={onSend} disabled={sending || !input.trim()} className="bg-orange-500 hover:bg-orange-600" aria-label="전송">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* right: uploads */}
      <div className="w-80 border-l p-3 flex flex-col gap-3">
        <div className="text-sm font-semibold">첨부 파일</div>
        <div className="flex gap-2 items-center">
          <Input id="file-input" type="file" accept=".png,.jpg,.jpeg,.pdf,.txt,image/*,application/pdf,text/plain" onChange={e => setFile(e.target.files?.[0] || null)} />
          <Button onClick={onUpload} disabled={!file || uploading} className="bg-slate-700 hover:bg-slate-800" aria-label="업로드">
            <Upload className="w-4 h-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="space-y-2">
            {uploads.map(u => {
              const ocr = (u.ocr_status || '').toLowerCase()
              let label = '처리 대기'
              let color = 'text-gray-500'
              if (ocr === 'pending' || ocr === 'processing') { label = 'OCR 처리 중'; color = 'text-blue-600' }
              else if (ocr === 'done' || ocr === 'completed') { label = '처리 완료'; color = 'text-green-600' }
              else if (ocr === 'failed') { label = '처리 실패'; color = 'text-red-600' }
              else if (ocr === 'skipped') { label = '처리 생략'; color = 'text-amber-600' }
              return (
                <Card key={u.upload_id}>
                  <CardContent className="p-3">
                    <div className="text-xs font-medium line-clamp-1">{u.filename}</div>
                    <div className={`text-[10px] ${color}`}>{label}</div>
                  </CardContent>
                </Card>
              )
            })}
            {uploads.length === 0 && (
              <div className="text-xs text-gray-500">아직 업로드된 파일이 없어요.</div>
            )}
          </div>
        </ScrollArea>
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}
    </div>
  )
}
