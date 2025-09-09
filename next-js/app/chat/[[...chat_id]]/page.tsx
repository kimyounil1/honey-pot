"use client"

import { useRouter, useParams, useSearchParams } from "next/navigation"
import Link from "next/link"
import { useState, useEffect, useMemo, useRef } from "react"
import dynamic from "next/dynamic"                    
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageCircle, Send, Plus, Search, FileText, TrendingUp, Shield, User, Menu, X, LogOut, ChevronDown, ChevronRight, ChevronUp, Droplet, Files, Webhook, Upload, Loader2 } from 'lucide-react'
import { Separator } from "@/components/ui/separator"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { sendChatRequest } from "@/lib/sendChatRequst"
import { v4 as uuidv4 } from 'uuid'
import InsuranceAddModal from "./insurance-add-modal"
import InsuranceCheckModal from "./insurance-check-modal copy"
import ProfileModal from "./profile-modal"
import FAQModal from "./faq-modal" 
import PolicyAnalysisModal from "./policy-analysis-modal"
import RefundFinderModal from "./refund-finder-modal"
import RecommendationModal from "./recommendation-modal"
import FileSubmitModal from "./file-submit-modal"

function BotAvatar() {
  return (
    <div className="flex-none w-8 h-8 min-w-[2rem] min-h-[2rem] rounded-full bg-gradient-to-r from-orange-400 to-orange-500 flex items-center justify-center shadow-sm ring-1 ring-black/5">
      <Droplet className="h-4 w-4 text-white" />
    </div>
  )
}

/* ===== 귀여운 로딩용: 벌 궤도 + 부드러운 상태 전환 ===== */
function BeeOrbit() {
  return (
    <div className="relative h-5 w-5">
      <div className="absolute inset-0 rounded-full border border-amber-300/70" />
      <div className="absolute inset-0 bee-orbit">
        <div className="absolute left-1/2 top-0 -translate-x-1/2">
          <span className="bee-counter text-base leading-none select-none">🐝</span>
        </div>
      </div>
    </div>
  );
}
type NonDoneState =
  | "commencing"
  | "classifying"
  | "analyzing"
  | "searching"
  | "building"
  | "failed";

function StateIndicator({ state, textMap }: { state: NonDoneState; textMap: Record<NonDoneState, string> }) {
  return (
    <div className="flex items-center gap-2 text-gray-600">
      <BeeOrbit />
      <span key={state} className="state-change">{textMap[state]}</span>
      <span className="loading-dots" aria-hidden="true">
        <span>.</span><span>.</span><span>.</span>
      </span>
    </div>
  );
}

// ✅ 팝업을 클라이언트에서만 렌더 (SSR 비활성)
const DeadlinePopup = dynamic(
  () => import("@/components/ui/deadline-popup"),
  { ssr: false }
);

interface ChatSession {
  id: number;
  title: string
  type: string[]
  lastMessage?: string
  timestamp: Date
  messageCount?: number
}

interface Message {
  id: string
  role: 'user' | 'assistant';
  content: string;
  attachment?: {
    product_id?: string | null;
    disease_code?: string | null;
  }
}

type MessageState = NonDoneState | "done" | "complete";
const TERMINAL_STATES: MessageState[] = ["done", "failed", "complete"];
const isTerminal = (s: MessageState) => TERMINAL_STATES.includes(s);

type BannerType = 'info' | 'success' | 'error' | 'loading'
function TopBanner({
  open,
  text,
  type = 'info',
}: {
  open: boolean;
  text: string;
  type?: BannerType;
}) {
  if (!open) return null;
  const base =
    'fixed top-4 left-1/2 -translate-x-1/2 z-50 ' +
    'max-w-md w-[calc(100%-2rem)] px-4 py-2 rounded-xl shadow-lg ' +
    'backdrop-blur-lg ring-1 ring-white/10 ' +
    'transition-all duration-300 ease-out animate-in fade-in slide-in-from-top-2'
  const color =
    type === 'success'
      ? 'bg-emerald-600/60 text-white'
      : type === 'error'
      ? 'bg-red-600/60 text-white'
      : type === 'loading'
      ? 'bg-sky-600/60 text-white'
      : 'bg-slate-800/60 text-white'

  return (
    <div className={`${base} ${color}`} role="status" aria-live="polite" style={{ pointerEvents: 'auto' }}>
      <div className="flex items-center gap-2 text-sm font-medium">
        {type === 'success' && (
          <span aria-hidden className="i-lucide:check-circle-2 size-4" />
        )}
        {type === 'error' && (
          <span aria-hidden className="i-lucide:triangle-alert size-4" />
        )}
        {type === 'loading' && (
          <span
            aria-hidden
            className="i-lucide:loader-2 size-4 animate-spin"
          />
        )}
        <span className="truncate">{text}</span>
      </div>
    </div>
  );
}
export default function ChatPage() {
  const searchParams = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showInsuranceModal, setShowInsuranceModal] = useState(false)
  const [showInsuranceCheckModal, setShowInsuranceCheckModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showFAQModal, setShowFAQModal] = useState(false)
  const [showPolicyAnalysisModal, setShowPolicyAnalysisModal] = useState(false)
  const [showRefundFinderModal, setShowRefundFinderModal] = useState(false)
  const [showRecommendationModal, setShowRecommendationModal] = useState(false)
  const [showFileSubmitModal, setShowFileSubmitModal] = useState(false)
  const [selectedPolicy, setSelectedPolicy] = useState<{ policy_id: string } | null>(null)

  // 배너 표시
  const [bannerOpen, setBannerOpen] = useState(false);
  const [bannerText, setBannerText] = useState('');
  const [bannerType, setBannerType] = useState<BannerType>('info');

  function showBanner(text: string, type: BannerType = 'info') {
    setBannerText(text);
    setBannerType(type);
    setBannerOpen(true);
  }

  function hideBanner() {
    setBannerOpen(false);
  }

  // Open specific modals when coming from external links
  useEffect(() => {
    const open = searchParams.get('open');
    if (open === 'insuranceCheck') setShowInsuranceCheckModal(true)
    if (open === 'insuranceAdd') setShowInsuranceModal(true)
    if (open === 'policyAnalysis') setShowPolicyAnalysisModal(true)
    if (open === 'refundFinder') setShowRefundFinderModal(true)
  }, [searchParams])

  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])

  const router = useRouter();
  const params = useParams();

  // Route-param 기반으로만 chatId 관리
  const chatId: number | undefined = (params?.chat_id as string[] | undefined)?.[0]
    ? Number((params.chat_id as string[])[0])
    : undefined;

  const [messages, setMessages] = useState<Message[]>([])
  const [lastMessage, setLastMessage] = useState<Message | null>(null)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [messageState, setMessageState] = useState<MessageState>()

  // ✅ 친절한 톤의 상태 문구
  const STATE_TEXT: Record<NonDoneState, string> = {
    commencing: "대화 준비 중이에요.",
    classifying: "질문 요지 파악 중이에요.",
    analyzing: "제공하신 자료 분석 중이에요~",
    searching: "근거를 찾는 중이에요~",
    building: "답변 정리 중이에요.",
    failed: "오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
  };

  // 파일 업로드 응답 임시보관
  const pendingUploadRef = useRef<any | null>(null)

  // 메세지 상태 폴링(페이지 로딩시)
  useEffect(() => {
    if (!chatId) return;

    let active = true;
    let timeoutId: number | undefined;
    const controller = new AbortController();

    const tick = async () => {
      if (!active) return;

      try {
        const res = await fetch(`/api/chat/${chatId}/messageState?t=${Date.now()}`, {
          cache: "no-store",
          headers: { "Cache-Control": "no-cache" },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        const data = await res.json();
        const state = data.state as MessageState;

        setMessageState(state);

        if (isTerminal(state)) {
          // 완료 시: 히스토리 갱신 + 서버에 complete 통지(있다면)
          await fetchChatHistory(chatId);
          active = false;

          try {
            await fetch(`/api/chat/${chatId}/messageState/complete?t=${Date.now()}`, {
              cache: "no-store",
              headers: { "Cache-Control": "no-cache" },
              signal: controller.signal,
            });
          } catch {}
          return;
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          console.error(e);
        }
      }

      if (active) {
        timeoutId = window.setTimeout(tick, 300);
      }
    };

    tick();

    return () => {
      active = false;
      if (timeoutId) clearTimeout(timeoutId);
      controller.abort();
    };
  }, [chatId]);
  
  // 메세지 전송 클릭시 상태 폴링
  const startPolling = (chatId: number) => {
    let active = true;
    const controller = new AbortController(); // cleanup에서만 사용

    const tick = async () => {
      if (!active) return;
      try {
        const res = await fetch(`/api/chat/${chatId}/messageState?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        const data = await res.json();
        setMessageState(data.state as MessageState);
        if (data.state === 'done' || data.state === 'failed') {
          await fetchChatHistory(chatId);
          active = false; // 종료
          const rss = await fetch(`/api/chat/${chatId}/messageState/complete?t=${Date.now()}`, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache' },
            signal: controller.signal,
          });
          return;
        }
      } catch (e: any) {
        if (e?.name !== 'AbortError') {
          console.error(e);
        }
      }

      if (active) {
        setTimeout(tick, 300);
      }
    };

    tick();

    return () => {
      active = false;
      controller.abort(); // 여기서만 abort
    };
  };

  const fetchChatHistory = async (id: number, opts: { allowEmptyReplace?: boolean } = {}) => {
    const { allowEmptyReplace = true } = opts;
    setIsLoading(true);
    try{
      const response = await fetch(`/api/chat/${id}?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' },
      })
      if(!response.ok){
        console.error("Failed to fetch chat history", response.status);
        return;
      }
      const historyData: Message[] = await response.json()
      if (historyData.length === 0 && !allowEmptyReplace) {
        return;
      }
      const messagesWithClientIds = historyData.map((message: any) => ({
        ...message,
        id: uuidv4()
      }));
      setMessages(messagesWithClientIds)
      setLastMessage(null)
    } catch(error){
      console.error("Failed to fetch chat history: ", error)
    } finally {
        setIsLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }
  const cleanupRef = useRef<(() => void) | null>(null);
  const messagesRef = useRef<Message[]>(messages);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  const submitMessage = async (text: string, opts?: { clearInput?: boolean }) => {
    const { clearInput = true } = opts ?? {};
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    hideBanner();

    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: trimmed,
      attachment: pendingUploadRef.current ?? undefined,
    };
    const placeholderId = uuidv4();
    const assistantPlaceholder: Message = { id: placeholderId, role: "assistant", content: "" };

    setMessages(prev => [...prev, userMessage]);
    setLastMessage(assistantPlaceholder);
    if (clearInput) setInput("");
    setIsLoading(true);
    setMessageState("commencing");

    // 이전 polling 중지 후 새 polling 시작
    cleanupRef.current?.();
    if (chatId !== undefined) {
      cleanupRef.current = startPolling(chatId);
    }

    const outgoing = [...messagesRef.current, userMessage];

    try {
      const response = await sendChatRequest(outgoing as any[], chatId);
      if (response?.chat_id && !chatId) {
        router.push(`/chat/${response.chat_id}`);
        fetchChatSessions?.();
      }

      if (response?.answer) {
        const assistantMessage: Message = {
          id: placeholderId,
          role: "assistant",
          content: response.answer,
        };
        setLastMessage(null);
        setMessages(prev => [...prev, assistantMessage]);
      }

      pendingUploadRef.current = null;
    } catch (err) {
      console.error(err);
      const errorMessage: Message = {
        id: placeholderId,
        role: "assistant",
        content: "오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      };
      setLastMessage(null);
      setMessages(prev => [...prev, errorMessage]);
      setMessageState("failed");
    } finally {
      setIsLoading(false);
    }
  };
  
  const [showChatHistory, setShowChatHistory] = useState(true)
  const [myInsuranceCompleted, setMyInsuranceCompleted] = useState(false)
  const [selectedInsuranceCompanies, setSelectedInsuranceCompanies] = useState<string[]>([])
  const [showAllQuickQuestions, setShowAllQuickQuestions] = useState(false)

  const fetchChatSessions = async () => {
    try {
      const response = await fetch('/api/chat/chats', {   
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' }, });
      if (!response.ok) {
        console.error("Failed to fetch chat sessions");
        return;
      }
      const data = await response.json();
      const formattedSessions: ChatSession[] = data.map((chat: any) => {
        let type: string[] = [];
        if (Array.isArray(chat.type)) {
          type = chat.type;
        } else if (typeof chat.type === 'string'){
          type = chat.type.split(',').map((s: string) => s.trim())
        }
        return {
          id: chat.id,
          title: chat.title,
          type: type,
          timestamp: new Date(chat.updated_at.replace(' ', 'T') + 'Z'),
        };
      });
      setChatSessions(formattedSessions);
    } catch (error) {
      console.error("Error fetching chat sessions:", error);
    }
  };

  useEffect(() => {
    if (showChatHistory) {
        fetchChatSessions();
    }
  }, [showChatHistory]);

  const handleSelectChat = (chatId: number) => {
    router.push(`/chat/${chatId}`);
  };

  const handlePolicyAnalysis = (p: { policy_id: string }) => {
    const message = `${p.policy_id}의 보험약관 분석을 요청합니다.`
    pendingUploadRef.current = {
        product_id: p.policy_id,
        disease_code: null,
    }
    submitMessage(message)
  }

  const handleRefundAnalysis = (textInput?: string) => {
    const message = textInput || ""
    submitMessage(message)
  }

  const handleRecommendationComplete = (recommendationType: string) => {
    handleFAQSelect(`보험 추천부탁: ${recommendationType}`)
  }

  const handleFileSubmit = async (file: File) => {
    try {
      const fd = new FormData()
      fd.append("file", file)
      showBanner("파일 첨부중...", "loading")
      
      const uploadRes = await fetch("/api/file", { method: "POST", body: fd })
      const ct = uploadRes.headers.get("content-type") ?? ""
      const raw = await uploadRes.text()

      if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.status}`)
      showBanner("파일 첨부 완료", "success")

      let data: any = raw
      if(ct.includes("application/json")){
        try {
          data = JSON.parse(raw)
        } catch(e){
          console.warn("Failed to parse JSON, using raw text: ", raw)
        }
      }
      if (data?.result_code === "SUCCESS") {
        pendingUploadRef.current = {
          product_id: data.product_id ?? null,
          disease_code: data.disease_code ?? null,
        } 
      }
    } catch (e) {
      window.alert(e)
    } finally {
      setIsUploading(false)
    }
  }

  const quickStartQuestions = [
    "제가 가입한 보험이 어떤 보장을 해주는지 모르겠어요.",
    "이 진단명(또는 질병명)으로 보험금 청구가 가능한가요?",
    "보험금을 청구하려면 어떤 서류가 필요한가요?",
    "충치치료도 일반 건강보험에서 보장이 되나요?",
    "같은 항목에 대해 여러번 청구할 수 있나요?",
    "내원시 받은 약처방도 내 보험에서 보장되나요?",
  ];

  const displayedQuestions = showAllQuickQuestions ? quickStartQuestions : quickStartQuestions.slice(0, 4);

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date()
    const diff = now.getTime() - timestamp.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (minutes < 60) return `${minutes}분 전`
    if (hours < 24) return `${hours}시간 전`
    return `${days}일 전`
  }

  const getChatTypeColor = (type: string) => {
    switch (type) {
      case "REFUND":
        return "bg-green-100 text-green-700"
      case "TERMS":
        return "bg-blue-100 text-blue-700"
      case "RECOMMEND":
        return "bg-purple-100 text-purple-700"
      default:
        return "bg-blue-100 text-blue-700"
    }
  }

  const getChatTypeName = (type: string) => {
    switch (type) {
      case "REFUND":
        return "환급"
      case "TERMS":
        return "약관"
      case "RECOMMEND":
        return "추천"
      default:
        return "일반"
    }
  }

  // 폼 제출
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitMessage(input, { clearInput: true });
  };

  // FAQ 클릭
  const handleFAQSelect = (question: string) => {
    submitMessage(question, { clearInput: false }); // 입력칸 유지
  };

  const resetToHome = () => {
    router.push('/chat');
    setMessages([]);
    setLastMessage(null);
  }
  const shouldShowRefundCTA = (text: string) => {
    try {
      if (!text) return false;
      return text.includes('자동 청구 페이지로 이동할까요');
    } catch { return false }
  }
  const displayedMessages = lastMessage ? [...messages, lastMessage] : messages;
  const shouldShowWelcome = !chatId && messages.length === 0;

  return (
    <div className="flex h-screen bg-gray-50">
      <TopBanner open={bannerOpen} text={bannerText} type={bannerType} />
      <DeadlinePopup />  {/* 하단 팝업 */}

      {/* Sidebar */}
      <div
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-50 w-96 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 flex flex-col lg:h-svh overflow-hidden min-h-0 flex-shrink-0`}
      >
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-2 cursor-pointer" onClick={resetToHome}>
            <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
              <Droplet className="h-5 w-5 text-white" />
            </div>
            <span className="text-base font-bold text-gray-800">꿀통</span>
          </div>
          <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          <div className="text-center">
            <Button
              className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 justify-center"
              onClick={resetToHome}
            >
              <Plus className="mr-2 h-4 w-4" />새 보험 채팅
            </Button>
          </div>
        </div>
        <div className="py-2"><Separator /></div>
        <ScrollArea className="flex-1">
          <div className="p-4 space-y-2">
            {/* 심사 페이지로 이동 */}
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words" onClick={() => router.push('/assessment')}>
              <FileText className="mr-3 h-4 w-4 text-orange-600" /> 보험 심사
            </Button>
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words" onClick={() => setShowInsuranceCheckModal(true)}> 
              <User className="mr-3 h-4 w-4 text-gray-800" />
              나의 보험 확인하기
            </Button>
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words" onClick={() => setShowInsuranceModal(true)}> 
              <User className="mr-3 h-4 w-4 text-gray-800" />
              나의 보험 추가하기
            </Button>
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words hidden" onClick={() => setShowPolicyAnalysisModal(true)}> 
              <FileText className="mr-3 h-4 w-4 text-blue-600" />
              내 보험 약관 분석
            </Button>
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words" onClick={() => router.push('/refund')}>
              <TrendingUp className="mr-3 h-4 w-4 text-green-600" />
              내 환급금 찾기
            </Button>
            <Button variant="ghost" className="w-full justify-start text-left text-gray-800 whitespace-normal break-words hidden" onClick={() => setShowRecommendationModal(true)}> 
              <Shield className="mr-3 h-4 w-4 text-purple-600" />
              보험 추천
            </Button>
            <div className="py-2"><Separator /></div>
            {/* 채팅 기록 고정 노출 */}
            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center">
              <MessageCircle className="mr-3 h-4 w-4" /> 채팅 기록
            </h3>
            <div className="mt-4">
              <div className="space-y-2">
                {chatSessions.map((chat) => (
                  <div
                    key={chat.id}
                    className={`p-3 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 ${ 
                      chatId === chat.id ? "bg-yellow-50 border border-yellow-200" : "bg-white border"
                    }`}
                    onClick={() => router.push(`/chat/${chat.id}`)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="text-sm font-medium break-words line-clamp-2">{chat.title}</h4>
                          <div className="flex items-center space-x-1 flex-wrap gap-y-1">
                            {(chat.type?.length ? chat.type : ["default"]).map((t) => (
                              <Badge key={t} className={`text-xs ${getChatTypeColor(t)}`}>{getChatTypeName(t)}</Badge>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-400">{formatTimestamp(chat.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>

        <div className="p-4 border-t mt-auto">
          <Button 
            variant="outline" 
            className="w-full bg-transparent"
            onClick={() => setShowProfileModal(true)}
          >
            <User className="mr-2 h-4 w-4" />
            내 정보
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-semibold text-gray-800">꿀통 보험 채팅창</h1>
          </div>
          <div className="flex items-center space-x-2">
            <Button 
              variant="outline" 
              className="text-red-600 border-red-600 hover:bg-red-50 px-3 py-1 text-sm h-auto"
              onClick={async () => { 
                try { 
                  await fetch("/api/logout", { method: "POST", cache: "no-store", credentials: "same-origin" }) 
                } catch(e) {
                  window.alert(e)
                } finally{
                  router.replace("/")
                }
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              로그아웃
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 bg-gradient-to-br from-orange-50 via-yellow-50 to-orange-100">
          {shouldShowWelcome ? (
            <div className="max-w-4xl mx-auto space-y-6" data-popup-anchor="main-card">
              {/* Welcome Card */}
              <Card className="text-center p-8 bg-white shadow-lg rounded-xl">
                <CardContent className="flex flex-col items-center justify-center p-0">
                  <div className="w-16 h-16 bg-gradient-to-r from-orange-400 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="font-bold text-2xl mb-2 text-gray-800">
                    보험 전문 AI 상담사, 꿀통
                  </h3>
                  <p className="text-base text-gray-600 mb-6">
                    보험의 모든걸 손쉬운 꿀통 채팅으로
                  </p>
                  <div className="grid grid-cols-2 gap-3 w-full">
                    {displayedQuestions.map((question) => (
                      <Button
                        key={question}
                        variant="outline"
                        className="text-left h-auto p-4 hover:bg-yellow-50 hover:border-yellow-300 bg-transparent justify-center text-sm"
                        onClick={() => handleFAQSelect(question)}
                      >
                        {question}
                      </Button>
                    ))}
                  </div>
                  {quickStartQuestions.length > 4 && (
                    <Button
                      variant="ghost"
                      className="mt-4 w-full justify-center text-gray-600 hover:text-gray-800"
                      onClick={() => setShowAllQuickQuestions(!showAllQuickQuestions)}
                    >
                      {showAllQuickQuestions ? (
                        <>접기 <ChevronUp className="ml-2 h-4 w-4" /></>
                      ) : (
                        <>더보기 <ChevronDown className="ml-2 h-4 w-4" /></>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>

              {/* Feature Cards */}
              <div className="grid md:grid-cols-3 gap-6">
                <Card className="text-center cursor-pointer hover:shadow-lg transition-all duration-300" onClick={() => setShowPolicyAnalysisModal(true)}>
                  <CardContent className="pt-6">
                    <FileText className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">보험 약관 분석</h3>
                    <p className="text-sm text-gray-600">복잡한 보험 약관을 쉽게 설명해드려요</p>
                  </CardContent>
                </Card>

                <Card className="text-center cursor-pointer hover:shadow-lg transition-all duration-300" onClick={() => setShowRefundFinderModal(true)}>
                  <CardContent className="pt-6">
                    <TrendingUp className="h-12 w-12 text-green-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">환급금 찾기</h3>
                    <p className="text-sm text-gray-600">놓치고 있던 환급금을 찾아드려요</p>
                  </CardContent>
                </Card>

                <Card className="text-center cursor-pointer hover:shadow-lg transition-all duration-300" onClick={() => setShowRecommendationModal(true)}>
                  <CardContent className="pt-6">
                    <Shield className="h-12 w-12 text-purple-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">보험 추천</h3>
                    <p className="text-sm text-gray-600">더 나은 보험 상품을 추천해드려요</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            // Chat message display
            <div className="max-w-3xl mx-auto space-y-4" data-popup-anchor="main-card">
                {displayedMessages.length === 0 && chatId && messageState !== "done" ? (
                    <div className="flex justify-start">
                      <div className="flex space-x-3 max-w-2xl">
                        <BotAvatar />
                        <div className="rounded-lg px-4 py-2 bg-white border shadow-sm">
                          <div className="whitespace-pre-wrap">
                            <StateIndicator state={(messageState ?? 'commencing') as NonDoneState} textMap={STATE_TEXT} />
                          </div>
                        </div>
                      </div>
                    </div>
                ) : (
                    displayedMessages.map((message) => (
                        <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`flex space-x-3 max-w-2xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}>
                              {message.role === "user" ? (
                                <Avatar className="flex-none w-8 h-8 min-w-[2rem] min-h-[2rem]">
                                  <AvatarFallback className="bg-orange-400 text-white">U</AvatarFallback>
                                </Avatar>
                              ) : (
                                <BotAvatar />
                              )}
                              <div className={`rounded-lg px-4 py-2 ${message.role === "user" ? "bg-orange-400 text-white" : "bg-white border shadow-sm"}`}>
                                <div className="text-sm">
                                  {message.role === "assistant"
                                    ? (message.content === "" && messageState && messageState !== "complete"
                                        ? <StateIndicator state={(messageState ?? 'commencing') as NonDoneState} textMap={STATE_TEXT} />
                                        : (
                                            <>
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
                                                      className={(className || "") + (inline
                                                        ? " px-1 py-0.5 rounded bg-slate-100"
                                                        : " block w-full whitespace-pre overflow-x-auto p-2 rounded bg-slate-100")}
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
                                                {message.content}
                                              </ReactMarkdown>
                                              {shouldShowRefundCTA(message.content) && (
                                                <div className="mt-3">
                                                  <Link href="/refund" className="inline-flex">
                                                    <Button size="sm" className="bg-gradient-to-r from-orange-400 to-orange-500 text-white">
                                                      환급 자동 청구로 이동
                                                    </Button>
                                                  </Link>
                                                </div>
                                              )}
                                            </>
                                          ))
                                    : <div className="whitespace-pre-wrap">{message.content}</div>}
                                </div>
                              </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
          )}
        </div>

        <div className="border-t bg-white p-4">
          
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="flex space-x-4">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="보험에 대해 궁금한 것을 물어보세요..."
                className="flex-1"
                disabled={isLoading}
              />
              <Button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  setShowFileSubmitModal(true)}
                }
                disabled={isUploading}
                className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
              >
                <Upload className="h-4 w-4" />
              </Button>
              <Button
                type="submit"
                disabled={isLoading || isUploading || !input?.trim()}
                className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              AI가 생성한 답변은 참고용이며, 정확한 정보는 전문가와 상담하세요.
            </p>
          </form>
        </div>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Modals */}
      <FileSubmitModal isOpen={showFileSubmitModal} onClose={() => setShowFileSubmitModal(false)} onSend={(files) => handleFileSubmit(files)}/>
      {/* <NewChatModal isOpen={showNewChatModal} onClose={() => setShowNewChatModal(false)} onStartChat={handleStartChatFromModal} /> */}
      <InsuranceCheckModal isOpen={showInsuranceCheckModal} onClose={() => setShowInsuranceCheckModal(false)} />
      <InsuranceAddModal isOpen={showInsuranceModal} onClose={() => setShowInsuranceModal(false)} onDone={(p) => { setShowInsuranceModal(false); if (p) setSelectedPolicy(p); }} />
      <ProfileModal isOpen={showProfileModal} onClose={() => setShowProfileModal(false)} />
      <FAQModal isOpen={showFAQModal} onClose={() => setShowFAQModal(false)} onSelectQuestion={handleFAQSelect} />
      <PolicyAnalysisModal isOpen={showPolicyAnalysisModal} onClose={() => setShowPolicyAnalysisModal(false)} onDone={(p) => handlePolicyAnalysis(p)} />
      <RefundFinderModal isOpen={showRefundFinderModal} onClose={() => setShowRefundFinderModal(false)} onAnalyze={(text) => handleRefundAnalysis(text)} />
      <RecommendationModal isOpen={showRecommendationModal} onClose={() => setShowRecommendationModal(false)} onComplete={handleRecommendationComplete} />
    </div>
  )
}
