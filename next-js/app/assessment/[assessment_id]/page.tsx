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
    const r = await fetch(`/api/assessments/${assessmentId}/messages`, { cache: "no-store" })
    if (r.ok) setMessages(await r.json())
  }
  const fetchUploads = async () => {
    if (!assessmentId) return
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
    if (!sending || !assessmentId) return
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
    if (!assessmentId) return
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
    setSending(true)
    await fetch(`/api/assessments/${assessmentId}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    })
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
            {/* initial guide when empty */}
            {messages.length === 0 && !sending && (
              <div className="flex justify-start">
                <Card className="bg-white max-w-[80%]">
                  <CardContent className="p-3 text-sm whitespace-pre-wrap">
                    안녕하세요! 보험 분석을 시작할까요?
                    {"\n"}궁금한 점을 적어주시거나 문서를 업로드해 주세요.
                    {"\n\n"}- 증빙 파일(진단서, 진료내역 등)을 첨부해 주세요.
                    {"\n"}- OCR 처리 중에는 분석이 지연될 수 있어요.
                  </CardContent>
                </Card>
              </div>
            )}
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

