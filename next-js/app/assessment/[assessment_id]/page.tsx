"use client"

import { useParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Upload, Send } from "lucide-react"
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
  const isDemo = assessmentId === 1

  // Sidebar data
  const [assessments, setAssessments] = useState<AssessmentItem[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([])
  useEffect(() => {
    const dummyAssessments: AssessmentItem[] = [
      { id: 1, title: "자동차보험 보상 문의", insurer: "A손해보험", created_at: new Date().toISOString(), last_message: "최근 메시지", message_count: 2 },
      { id: 2, title: "실손보험 증빙 서류", insurer: "B손해보험", created_at: new Date(Date.now() - 86400000).toISOString() },
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

  const bottomRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const fetchMessages = async () => {
    if (!assessmentId) return
    if (isDemo) {
      const now = new Date()
      setMessages([
        { id: 1, role: 'user', content: '자동차보험 보상 문의드립니다. 합의금이 적정한지 봐주세요.', timestamp: new Date(now.getTime() - 1000 * 60 * 22).toISOString() },
        { id: 2, role: 'assistant', content: '첨부된 카톡 대화와 심사 내역서를 확인했어요. 초기 제시액에는 위자료와 휴업손해 일부가 반영되지 않았습니다. 몇 가지 보완 시 추가 수령 가능성이 있습니다.', timestamp: new Date(now.getTime() - 1000 * 60 * 20).toISOString() },
        { id: 3, role: 'assistant', content: '예상 추가 수령 범위는 약 35만~60만원입니다. 세부 근거는 아래와 같아요:\n- 위자료: 경미 상해 기준 가이드 상향 여지\n- 교통비/치료비 누락분\n- 휴업손해: 소득 증빙 시 부분 반영 가능', timestamp: new Date(now.getTime() - 1000 * 60 * 18).toISOString() },
        { id: 4, role: 'user', content: '그러면 뭐 어떻게 해야하나요?', timestamp: new Date(now.getTime() - 1000 * 60 * 16).toISOString() },
        { id: 5, role: 'assistant', content: '진행 방법 안내드릴게요.\n\n요약 금액(가정):\n- 총 손해 추정액: 1,800,000원\n- 현재 제시액: 1,250,000원\n- 추가 수령 예상: 350,000~600,000원\n- 목표 합계: 1,600,000~1,850,000원\n\n다음 순서로 진행해 주세요:\n1) 치료비/약제비/교통비 영수증 재정리 후 스캔 업로드\n2) 소득증빙(재직·급여명세 등) 제출 → 휴업손해 반영 요청\n3) 위자료 상향 사유(통원빈도/통증/불편사항) 메모 정리\n4) 위 내용 근거로 조정요청서 또는 담당자에게 카톡/메일 발송\n\n필요하시면 제가 제출용 문구도 정리해 드릴게요.', timestamp: new Date(now.getTime() - 1000 * 60 * 15).toISOString() },
      ])
      return
    }
    const r = await fetch(`/api/assessments/${assessmentId}/messages`, { cache: "no-store" })
    if (r.ok) setMessages(await r.json())
  }
  const fetchUploads = async () => {
    if (!assessmentId) return
    if (isDemo) {
      const now = new Date()
      setUploads([
        { upload_id: 'demo-kt', filename: '카톡내용.txt', file_type: 'text/plain', file_size: 12456, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 30).toISOString() },
        { upload_id: 'demo-img', filename: '심사-내역서.png', file_type: 'image/png', file_size: 342399, upload_status: 'completed', ocr_status: 'completed', created_at: new Date(now.getTime() - 1000 * 60 * 28).toISOString() },
      ])
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
    <div className="flex h-screen">
      <AssessmentSidebar
        assessments={assessments}
        chatHistory={chatHistory}
        onNewAssessmentClick={() => { /* open modal if needed */ }}
        onLogout={handleLogout}
      />

      {/* center: messages */}
      <div className="flex-1 flex flex-col">
        <div className="border-b p-3 text-sm text-gray-600">분석 #{assessmentId}</div>
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-3">
            {/* guide chat should always appear at top */}
            <div className="flex justify-start">
              <Card className="bg-white max-w-[80%] border-dashed">
                <CardContent className="p-3 text-sm whitespace-pre-wrap">
                  안녕하세요! 보험 분석을 시작할까요?
                  {"\n"}궁금한 점을 적어주시거나 문서를 업로드해 주세요.
                  {"\n\n"}- 증빙 파일(진단서, 진료내역 등)을 첨부해 주세요.
                  {"\n"}- OCR 처리 중에는 분석이 지연될 수 있어요.
                </CardContent>
              </Card>
            </div>
            {messages.map(m => (
              <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <Card className={m.role === 'user' ? 'bg-orange-50 max-w-[80%]' : 'bg-white max-w-[80%]'}>
                  <CardContent className="p-3 text-sm whitespace-pre-wrap">
                    {m.content}
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
    </div>
  )
}
