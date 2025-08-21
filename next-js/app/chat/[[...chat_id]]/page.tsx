"use client"

import { useRouter, useParams } from "next/navigation"
import { useState, useEffect, useMemo, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageCircle, Send, Plus, Search, FileText, TrendingUp, Shield, User, Menu, X, LogOut, ChevronDown, ChevronRight, ChevronUp, Droplet } from 'lucide-react'
import { sendChatRequest } from "@/lib/sendChatRequst"
import { v4 as uuidv4 } from 'uuid'
import NewChatModal from "./new-chat-modal"
import InsuranceCompanyModal from "./insurance-company-modal"
import ProfileModal from "./profile-modal"
import FAQModal from "./faq-modal" 
import PolicyAnalysisModal from "./policy-analysis-modal"
import RefundFinderModal from "./refund-finder-modal"
import RecommendationModal from "./recommendation-modal"

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
}

type NonDoneState =
  | "commencing"
  | "classifying"
  | "analyzing"
  | "searching"
  | "building"
  | "failed";

type MessageState = NonDoneState | "done" | "complete";
const TERMINAL_STATES: MessageState[] = ["done", "failed", "complete"];
const isTerminal = (s: MessageState) => TERMINAL_STATES.includes(s);

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showNewChatModal, setShowNewChatModal] = useState(false)
  const [showInsuranceModal, setShowInsuranceModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showFAQModal, setShowFAQModal] = useState(false)
  const [showPolicyAnalysisModal, setShowPolicyAnalysisModal] = useState(false)
  const [showRefundFinderModal, setShowRefundFinderModal] = useState(false)
  const [showRecommendationModal, setShowRecommendationModal] = useState(false)

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
  const [messageState, setMessageState] = useState<MessageState>()

  const STATE_TEXT: Record<NonDoneState, string> = {
    commencing: "...",
    classifying: "메세지를 분류중입니다...",
    analyzing: "제공하신 자료를 분석중입니다...",
    searching: "데이터를 바탕으로 결과를 분석중입니다...",
    building: "응답을 받아오는 중...",
    failed: "에러 발생",
  };

//   // chatId 변경 시 히스토리 로드
//   useEffect(() => {
//     if (chatId) {
//         fetchChatHistory(chatId, { allowEmptyReplace: false });
//     } else {
//         setMessages([]);
//     }
//   }, [chatId]);

  // 상태 폴링
  //########### 두번째부터는 route 안타니까 useEffect도 안 타버림. ######################
  
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

        // 이미 서버가 complete를 주는 상황이면 아래 호출은 선택사항
        // 실패(Abort 등)하더라도 폴링 종료에는 영향 없게 try/catch
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
      // 에러여도 active가 true면 재시도 예약
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
  
  const startPolling = (chatId: number) => {
    let active = true;
    const controller = new AbortController(); // cleanup에서만 사용

    const tick = async () => {
    console.log("startPolling 호출", active)
      if (!active) return;
      try {
        const res = await fetch(`/api/chat/${chatId}/messageState?t=${Date.now()}`, {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache' },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`API Error: ${res.status}`);
        const data = await res.json();
        // console.log("******결과:",data)
        setMessageState(data.state as MessageState);
        // 백엔드에 자징되는 complete state 추가
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
        // AbortError면 종료하지 않음(대개 언마운트/전환 시 발생)
        if (e?.name !== 'AbortError') {
          console.error(e);
          // 일시적 에러면 약간 대기 후 재시도
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
      // 진행 중(서버 히스토리 미기록)엔 로컬 플레이스홀더 유지
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
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: uuidv4(), role: 'user', content: input, };
    const placeholderId = uuidv4();
    const assistantPlaceholder: Message = { id: placeholderId, role: 'assistant', content: '', };
    setMessages(prev => [...prev, userMessage]);
    setLastMessage(assistantPlaceholder);
    setInput("");
    setIsLoading(true);
    setMessageState("commencing");
      // 이전 polling 중지
    cleanupRef.current?.();

    // 새로운 polling 시작
    // console.log(typeof(chatId))
    if(chatId !== undefined){
        cleanupRef.current = startPolling(chatId);
    }


    try {
      const response = await sendChatRequest([...messages, userMessage], chatId);

      // 새 채팅이면 라우팅만 (상태는 route-param이 관리)
      if (response?.chat_id && !chatId) {
        router.push(`/chat/${response.chat_id}`);
        fetchChatSessions?.();
      }
      // ################ 이 밑의 모든 내용들이 저 response랑 별개로 chat_id 기반으로 useEffect #####################
      if (response?.answer) {
        const assistantMessage: Message = {
          id: placeholderId,
          role: "assistant",
          content: response.answer,
        };
        setLastMessage(null);
        setMessages(prev => [...prev, assistantMessage]);
      }
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

  const handleLogout = async () => {
    await fetch("/api/logout");
    router.push("/");
  };

  const handleNewChat = () => {
    setShowNewChatModal(true)
  }

  const handleStartChatFromModal = async (type: string, title?: string, initialMessage?: string) => {
    if (!initialMessage || isLoading) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: initialMessage,
    };
    const placeholderId = uuidv4();
    const assistantPlaceholder: Message = {
      id: placeholderId,
      role: 'assistant',
      content: '',
    };

    setMessages([userMessage]);
    setLastMessage(assistantPlaceholder);
    setInput('');
    setIsLoading(true);

    try {
      const messagesForApi = [userMessage];
      const response = await sendChatRequest(messagesForApi, chatId);

      if (response && response.answer) {
        const assistantMessage: Message = {
          id: placeholderId,
          role: 'assistant',
          content: response.answer,
        };
        setLastMessage(null);
        setMessages(prev => [...prev, assistantMessage]);

        if (response.chat_id && !chatId) {
          const newChatId = response.chat_id;
          router.push(`/chat/${newChatId}`)
        }
        // fetchChatSessions();
      } else if (response?.chat_id && chatId) {
        // 비동기 응답: placeholder 유지, 히스토리 로딩 시 치환
      } else {
        const errorMessage: Message = {
          id: placeholderId,
          role: 'assistant',
          content: response?.error || '오류가 발생했습니다.',
        };
        setLastMessage(null);
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error("Error in handleStartChatFromModal: ", error);
      const errorMessage: Message = {
        id: placeholderId,
        role: 'assistant',
        content: '오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
      };
      setLastMessage(null);
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

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

  const handleInsuranceCompanyComplete = (companies: string[] | null) => {
    if (companies === null) {
      setMyInsuranceCompleted(true)
      setSelectedInsuranceCompanies([])
    } else {
      setSelectedInsuranceCompanies(companies)
      setMyInsuranceCompleted(true)
    }
  }

  const handlePolicyAnalysis = (files: File[], textInput?: string) => {
    const fileNames = files.map(f => f.name).join(', ')
    const message = textInput ? `내 보험 증권 분석을 요청합니다. 내용: ${textInput}` : `내 보험 증권 분석을 요청합니다. 파일: ${fileNames}`
    handleStartChatFromModal("analysis", "보험 약관 분석 요청", message)
  }

  const handleRefundAnalysis = (medicalCertificate: File | null, detailedBill: File | null, textInput?: string) => {
    let message = textInput || ""
    if (medicalCertificate && detailedBill) {
      message += `\n진료확인서(${medicalCertificate?.name})와 진료비 세부 내역서(${detailedBill?.name})도 첨부합니다.`
    }
    handleStartChatFromModal("refund", "환급금 분석 요청", message.trim())
  }

  const handleRecommendationComplete = (recommendationType: string) => {
    handleStartChatFromModal("general", `보험 추천 (${recommendationType})`, `"${recommendationType}"에 대한 보험 추천을 완료했습니다. 결과에 대해 더 궁금한 점이 있습니다.`)
  }

  const quickStartQuestions = [
    "제가 가입한 보험이 어떤 보장을 해주는지 모르겠어요.",
    "이 진단명(또는 질병명)으로 보험금 청구가 가능한가요?",
    "보험금을 청구하려면 어떤 서류가 필요한가요?",
    "제가 아직 청구하지 않은 보험금이 있나요?",
    "실손보험은 몇 번까지 청구할 수 있나요?",
    "보험 가입 내역을 한 번에 확인할 수 있나요?",
    "이 약은 실손보험에서 보장되나요?",
    "제 보험료가 왜 이렇게 비싸졌나요?",
    "가족(부모/자녀) 보험도 함께 확인할 수 있나요?",
    "보험 리모델링을 받을 수 있나요?",
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
        return "환급금"
      case "TERMS":
        return "약관분석"
      case "RECOMMEND":
        return "추천"
      default:
        return "일반상담"
    }
  }

  const handleFAQSelect = (question: string) => {
    handleStartChatFromModal("general", question.length > 30 ? question.substring(0, 30) + "..." : question, question)
  }

  const resetToHome = () => {
    router.push('/chat');
    setMessages([]);
    setLastMessage(null);
    // setHasActiveThread(false);
  }

  const displayedMessages = lastMessage ? [...messages, lastMessage] : messages;
  const shouldShowWelcome = !chatId && messages.length === 0;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-50 w-80 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 flex flex-col`}
      >
        <div className="flex items-center justify-between p-4 border-b">
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
              onClick={handleNewChat}
            >
              <Plus className="mr-2 h-4 w-4" />새 보험 채팅
            </Button>
          </div>
        </div>

        <nav className="px-4 space-y-2">
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => setShowInsuranceModal(true)}> 
            <User className="mr-3 h-4 w-4 text-gray-800" />
            나의 보험
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => setShowPolicyAnalysisModal(true)}> 
            <FileText className="mr-3 h-4 w-4 text-blue-600" />
            내 보험 약관 분석
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => setShowRefundFinderModal(true)}> 
            <TrendingUp className="mr-3 h-4 w-4 text-green-600" />
            환급금 찾기
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => setShowRecommendationModal(true)}> 
            <Shield className="mr-3 h-4 w-4 text-purple-600" />
            보험 추천
          </Button>
          <Button 
            variant="ghost" 
            className="w-full justify-start"
            onClick={() => setShowChatHistory(!showChatHistory)}
          >
            <MessageCircle className="mr-3 h-4 w-4" />
            채팅 기록
            {showChatHistory ? (
              <ChevronDown className="ml-auto h-4 w-4" />
            ) : (
              <ChevronRight className="ml-auto h-4 w-4" />
            )}
          </Button>
        </nav>

        {showChatHistory && (
          <div className="px-4 mt-6 flex-1 flex-col hidden lg:flex">
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input placeholder="채팅 검색" className="pl-10" />
            </div>
            
            <h4 className="text-sm font-medium text-gray-500 mb-3">최근 채팅</h4>
            <ScrollArea className="flex-1">
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
                          <h4 className="text-sm font-medium truncate">{chat.title}</h4>
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
            </ScrollArea>
          </div>
        )}

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
              onClick={async () => { await fetch("/api/logout"); router.push("/"); }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              로그아웃
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 bg-gradient-to-br from-orange-50 via-yellow-50 to-orange-100">
          {shouldShowWelcome ? (
            <div className="max-w-4xl mx-auto space-y-6">
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
            <div className="max-w-3xl mx-auto space-y-4">
                {displayedMessages.length === 0 && chatId && messageState !== "done" ? (
                    <div className="flex justify-start">
                    <div className="flex space-x-3 max-w-2xl">
                        <Avatar className="w-8 h-8">
                        <AvatarImage src="/placeholder.svg?height=32&width=32" />
                        </Avatar>
                        <div className="rounded-lg px-4 py-2 bg-white border shadow-sm">
                        <div className="whitespace-pre-wrap">
                            {STATE_TEXT[messageState as NonDoneState]}
                        </div>
                        </div>
                    </div>
                    </div>
                ) : (
                    displayedMessages.map((message) => (
                        <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`flex space-x-3 max-w-2xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}>
                            <Avatar className="w-8 h-8">
                            {message.role === "user" ? (
                                <AvatarFallback className="bg-blue-500 text-white">U</AvatarFallback>
                            ) : (
                                <AvatarImage src="/placeholder.svg?height=32&width=32" />
                            )}
                            </Avatar>
                            <div className={`rounded-lg px-4 py-2 ${message.role === "user" ? "bg-blue-500 text-white" : "bg-white border shadow-sm"}`}>
                                <div className="whitespace-pre-wrap">
                                    {message.role === "assistant"
                                    ? (message.content === "" && messageState && messageState !== "complete"
                                        ? STATE_TEXT[messageState as NonDoneState]
                                        : (message.content))
                                    : message.content}
                                </div>
                            </div>
                        </div>
                    </div>
                    ))
                )}
            </div>
            // <div className="max-w-3xl mx-auto space-y-4">
            //   {messages.map((message) => (
            //     <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            //       <div className={`flex space-x-3 max-w-2xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}>
            //         <Avatar className="w-8 h-8">
            //           {message.role === "user" ? (
            //             <AvatarFallback className="bg-blue-500 text-white">U</AvatarFallback>
            //           ) : (
            //             <AvatarImage src="/placeholder.svg?height=32&width=32" />
            //           )}
            //         </Avatar>
            //         <div className={`rounded-lg px-4 py-2 ${message.role === "user" ? "bg-blue-500 text-white" : "bg-white border shadow-sm"}`}>
            //           <div className="whitespace-pre-wrap">
            //             {message.role === "assistant"
            //               ? (message.content === "" && messageState && messageState !== "done"
            //                   ? STATE_TEXT[messageState as NonDoneState]
            //                   : (message.content || "..."))
            //               : message.content}
            //           </div>
            //         </div>
            //       </div>
            //     </div>
            //   ))}
            // </div>
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
                type="submit"
                disabled={isLoading || !input?.trim()}
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
      <NewChatModal isOpen={showNewChatModal} onClose={() => setShowNewChatModal(false)} onStartChat={handleStartChatFromModal} />
      <InsuranceCompanyModal isOpen={showInsuranceModal} onClose={() => setShowInsuranceModal(false)} onComplete={(c) => { setShowInsuranceModal(false); if (c) setSelectedInsuranceCompanies(c); }} initialSelectedCompanies={selectedInsuranceCompanies} onStartChat={handleStartChatFromModal} />
      <ProfileModal isOpen={showProfileModal} onClose={() => setShowProfileModal(false)} />
      <FAQModal isOpen={showFAQModal} onClose={() => setShowFAQModal(false)} onSelectQuestion={handleFAQSelect} />
      <PolicyAnalysisModal isOpen={showPolicyAnalysisModal} onClose={() => setShowPolicyAnalysisModal(false)} onAnalyze={(files, text) => handlePolicyAnalysis(files, text)} />
      <RefundFinderModal isOpen={showRefundFinderModal} onClose={() => setShowRefundFinderModal(false)} onAnalyze={(mc, db, text) => handleRefundAnalysis(mc, db, text)} />
      <RecommendationModal isOpen={showRecommendationModal} onClose={() => setShowRecommendationModal(false)} onComplete={handleRecommendationComplete} selectedCompanies={selectedInsuranceCompanies} />

      {/* 🔎 Tiny debug overlay (삭제해도 됩니다)
      <div className="fixed bottom-2 right-2 text-[11px] bg-black/70 text-white px-2 py-1 rounded shadow z-50 select-none">
        chatId: {String(chatId ?? 'none')} | msgs: {messages.length} | active:{String(hasActiveThread)} | state:{messageState}
      </div> */}
    </div>
  )
}