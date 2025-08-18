"use client"

import { useRouter, useParams } from "next/navigation"
import { useState, useEffect } from "react" // Import useEffect
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageCircle, Send, Plus, Search, FileText, TrendingUp, Shield, User, Menu, X, Trash2, MoreVertical, Droplet, History, LogOut, ChevronDown, ChevronRight, ChevronUp } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { sendChatRequest } from "@/lib/sendChatRequst"
import { v4 as uuidv4 } from 'uuid'
import Link from "next/link"
import NewChatModal from "./new-chat-modal"
import InsuranceCompanyModal from "./insurance-company-modal"
import ProfileModal from "./profile-modal"
import FAQModal from "./faq-modal"
import PolicyAnalysisModal from "./policy-analysis-modal"
import RefundFinderModal from "./refund-finder-modal"
import RecommendationModal from "./recommendation-modal"

interface ChatSession {
  title: string
  type: string
  lastMessage: string
  timestamp: Date
  messageCount: number
}

interface Message {
  id: string
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showNewChatModal, setShowNewChatModal] = useState(false)
  const [showInsuranceModal, setShowInsuranceModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showFAQModal, setShowFAQModal] = useState(false)
  const [showPolicyAnalysisModal, setShowPolicyAnalysisModal] = useState(false)
  const [showRefundFinderModal, setShowRefundFinderModal] = useState(false)
  const [showRecommendationModal, setShowRecommendationModal] = useState(false)

  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      // id: "1",
      title: "실손보험 환급금 문의",
      type: "refund",
      lastMessage: "네, 확인해보니 약 150만원의 환급금이...",
      timestamp: new Date(Date.now() - 1000 * 60 * 30),
      messageCount: 12,
    },
    {
      // id: "2",
      title: "보험 약관 분석",
      type: "analysis",
      lastMessage: "해당 약관에 따르면 특약 조건이...",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
      messageCount: 8,
    },
  ])

  const router = useRouter();
  const params = useParams();
  const [chatId, setChatId] = useState<number | undefined>();

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const paramChatIdArray = params?.chat_id as string[] | undefined;
    const paramChatId = paramChatIdArray?.[0] ? Number(paramChatIdArray[0]) : undefined;
    setChatId(paramChatId);
  }, [params?.chat_id]);


  const fetchChatHistory = async (id: number) => {
    setIsLoading(true)
    try{
      const response = await fetch(`/api/chat/${id}`)
      if(!response.ok){
        router.push('/chat')
        return;
      }
      const historyData: Message[] = await response.json()
      const messagesWithClientIds = historyData.map((message: any) => ({
        ...message,
        id: uuidv4()
      }));
      setMessages(messagesWithClientIds)
    } catch(error){
      console.error("Failed to fetch chat history: ", error)
      router.push("/chat")
    } finally {
      setIsLoading(false)
    }
  }

    useEffect(() => {
    if (chatId) {
      fetchChatHistory(chatId);
    } else {
      setMessages([]);
    }
  }, [chatId]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: input,
    }

    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)

    try {
      const response = await sendChatRequest(newMessages, chatId)

      if (response && response.answer) {
        const assistantMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: response.answer,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        if (response.chat_id && !chatId) {
          const newChatId = response.chat_id;
          setChatId(newChatId);
          // router.push(`/chat/${newChatId}`, { scroll: false });
          window.history.pushState(null, '', `/chat/${newChatId}`)
        }
      } else if(response.chat_id && chatId){
        
      } else {
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: response.error || '오류가 발생했습니다.',
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
        console.error("Error in handleSubmit: ", error);
        const errorMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: '오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        };
        setMessages((prev) => [...prev, errorMessage]);
    } finally {
        setIsLoading(false)
    }
  }

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

  const handleStartChatFromModal = (type: string, title?: string, initialMessage?: string) => {
    // TODO: 여기도 위에처럼 바꿔줘야 함
    
    if (initialMessage) {
      setMessages([
        {
          id: uuidv4(), // ID is present, which is good
          role: "user",
          content: initialMessage,
        }
      ]);
    } else {
      setMessages([]);
    }

    // const newSession: ChatSession = {
    //   // id: newChatId,
    //   title: title || `새 상담 - ${new Date().toLocaleDateString()}`,
    //   type,
    //   lastMessage: initialMessage || "",
    //   timestamp: new Date(),
    //   messageCount: initialMessage ? 1 : 0,
    // }
    // setChatSessions((prev) => [newSession, ...prev])
    
    // // const userMessage: Message = {
    // //   role: 'user',
    // //   content: input,
    // //   // chat_id: chatId,
    // //   first_message: false
    // // }

    // const newMessages = [...messages, userMessage]
    // sendChatRequest(newMessages, setMessages, setIsLoading)
  }

  // TODO: 추후에 다른 방식으로 구현하도록 할것
  // const handleDeleteChat = (chatId: string) => {
  //   setChatSessions((prev) => prev.filter((chat) => chat.id !== chatId))
  //   if (currentChatId === chatId) {
  //     setCurrentChatId(null)
  //     setMessages([])
  //   }
  // }

  // const handleSelectChat = (chatId: string) => {
    // setCurrentChatId(chatId)
    // Here you would typically fetch the message history for the selected chat
    // For now, we just clear the messages as per the original logic.
    // setMessages([])

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
    console.log("보험 약관 분석 시작:", files.map(f => f.name), textInput)
    const fileNames = files.map(f => f.name).join(', ')
    const message = textInput ? `내 보험 증권 분석을 요청합니다. 내용: ${textInput}` : `내 보험 증권 분석을 요청합니다. 파일: ${fileNames}`
    handleStartChatFromModal("analysis", "보험 약관 분석 요청", message)
  }

  const handleRefundAnalysis = (medicalCertificate: File | null, detailedBill: File | null, textInput?: string) => {
    console.log("환급금 분석 시작:", medicalCertificate?.name, detailedBill?.name, textInput)
    let message = textInput || ""
    if (medicalCertificate && detailedBill) {
      message += `\n진료확인서(${medicalCertificate?.name})와 진료비 세부 내역서(${detailedBill?.name})도 첨부합니다.`
    }
    handleStartChatFromModal("refund", "환급금 분석 요청", message.trim())
  }

  const handleRecommendationComplete = (recommendationType: string) => {
    console.log("보험 추천 완료:", recommendationType)
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

  const handleFeatureClick = (feature: string) => {
    console.log(`Feature clicked: ${feature}, myInsuranceCompleted: ${myInsuranceCompleted}`);
    switch (feature) {
      case '나의 보험':
        setShowInsuranceModal(true);
        break;
      case '내 보험 약관 분석':
        setShowPolicyAnalysisModal(true);
        break;
      case '환급금 찾기':
        setShowRefundFinderModal(true);
        break;
      case '보험 추천':
        setShowRecommendationModal(true);
        break;
      default:
        console.log(`${feature} 기능 시작`);
    }
  };

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
      case "refund":
        return "bg-green-100 text-green-700"
      case "analysis":
        return "bg-blue-100 text-blue-700"
      case "comparison":
        return "bg-purple-100 text-purple-700"
      default:
        return "bg-blue-100 text-blue-700"
    }
  }

  const getChatTypeName = (type: string) => {
    switch (type) {
      case "refund":
        return "환급금"
      case "analysis":
        return "약관분석"
      case "comparison":
        return "비교"
      default:
        return "일반상담"
    }
  }

  const handleFAQSelect = (question: string) => {
    handleStartChatFromModal("general", question.length > 30 ? question.substring(0, 30) + "..." : question, question)
  }

  const resetToHome = () => {
    // setCurrentChatId(null);
    router.push('/chat')
    return;
  }
  // console.log('Current Messages State:', JSON.stringify(messages, null, 2));
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
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => handleFeatureClick('나의 보험')}> 
            <User className="mr-3 h-4 w-4 text-gray-800" />
            나의 보험
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => handleFeatureClick('내 보험 약관 분석')}> 
            <FileText className="mr-3 h-4 w-4 text-blue-600" />
            내 보험 약관 분석
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => handleFeatureClick('환급금 찾기')}> 
            <TrendingUp className="mr-3 h-4 w-4 text-green-600" />
            환급금 찾기
          </Button>
          <Button variant="ghost" className="w-full justify-start text-gray-800" onClick={() => handleFeatureClick('보험 추천')}> 
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
          <div className="px-4 mt-6 flex-1 flex flex-col">
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input placeholder="채팅 검색" className="pl-10" />
            </div>
            
            {/* // TODO : chatID 관련된 부분 임시 주석처리 */}
            {/* <h4 className="text-sm font-medium text-gray-500 mb-3">최근 채팅</h4>
            <ScrollArea className="flex-1">
              <div className="space-y-2">
                {chatSessions.map((chat) => (
                  <div
                    key={chat.id}
                    className={`p-3 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 ${ 
                      currentChatId === chat.id ? "bg-yellow-50 border border-yellow-200" : "bg-white border"
                    }`}
                    onClick={() => handleSelectChat(chat.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="text-sm font-medium truncate">{chat.title}</h4>
                          <Badge className={`text-xs ${getChatTypeColor(chat.type)}`}>{getChatTypeName(chat.type)}</Badge>
                        </div>
                        <p className="text-xs text-gray-500 truncate">{chat.lastMessage || "새 채팅"}</p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-400">{formatTimestamp(chat.timestamp)}</span>
                          <span className="text-xs text-gray-400">{chat.messageCount}개 메시지</span>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                            <MoreVertical className="h-3 w-3" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleDeleteChat(chat.id)} className="text-red-600">
                            <Trash2 className="mr-2 h-4 w-4" />
                            삭제
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea> */}
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
              onClick={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              로그아웃
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 bg-gradient-to-br from-orange-50 via-yellow-50 to-orange-100">
          {messages.length === 0 ? (
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
                    {displayedQuestions.map((question, index) => (
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
                        <>
                          접기 <ChevronUp className="ml-2 h-4 w-4" />
                        </>
                      ) : (
                        <>
                          더보기 <ChevronDown className="ml-2 h-4 w-4" />
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>

              {/* Feature Cards - 3개 박스 */}
              <div className="grid md:grid-cols-3 gap-6">
                <Card
                  className="text-center cursor-pointer hover:shadow-lg transition-all duration-300"
                  onClick={() => handleFeatureClick('내 보험 약관 분석')}
                >
                  <CardContent className="pt-6">
                    <FileText className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">보험 약관 분석</h3>
                    <p className="text-sm text-gray-600">복잡한 보험 약관을 쉽게 설명해드려요</p>
                  </CardContent>
                </Card>

                <Card
                  className="text-center cursor-pointer hover:shadow-lg transition-all duration-300"
                  onClick={() => handleFeatureClick('환급금 찾기')}
                >
                  <CardContent className="pt-6">
                    <TrendingUp className="h-12 w-12 text-green-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">환급금 찾기</h3>
                    <p className="text-sm text-gray-600">놓치고 있던 환급금을 찾아드려요</p>
                  </CardContent>
                </Card>

                <Card
                  className="text-center cursor-pointer hover:shadow-lg transition-all duration-300"
                  onClick={() => handleFeatureClick('보험 추천')}
                >
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
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`flex space-x-3 max-w-2xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}
                  >
                    <Avatar className="w-8 h-8">
                      {message.role === "user" ? (
                        <AvatarFallback className="bg-blue-500 text-white">U</AvatarFallback>
                      ) : (
                        <AvatarImage src="/placeholder.svg?height=32&width=32" />
                      )}
                    </Avatar>
                    <div
                      className={`rounded-lg px-4 py-2 ${ 
                        message.role === "user" ? "bg-blue-500 text-white" : "bg-white border shadow-sm"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex space-x-3 max-w-2xl">
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="/placeholder.svg?height=32&width=32" />
                    </Avatar>
                    <div className="bg-white border shadow-sm rounded-lg px-4 py-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
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

      <NewChatModal
        isOpen={showNewChatModal}
        onClose={() => setShowNewChatModal(false)}
        onStartChat={handleStartChatFromModal}
      />

      <InsuranceCompanyModal
        isOpen={showInsuranceModal}
        onClose={() => setShowInsuranceModal(false)}
        onComplete={handleInsuranceCompanyComplete}
        initialSelectedCompanies={selectedInsuranceCompanies}
        onStartChat={handleStartChatFromModal}
      />

      <ProfileModal
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
      />

      <FAQModal
        isOpen={showFAQModal}
        onClose={() => setShowFAQModal(false)}
        onSelectQuestion={handleFAQSelect}
      />

      <PolicyAnalysisModal
        isOpen={showPolicyAnalysisModal}
        onClose={() => setShowPolicyAnalysisModal(false)}
        onAnalyze={handlePolicyAnalysis}
      />

      <RefundFinderModal
        isOpen={showRefundFinderModal}
        onClose={() => setShowRefundFinderModal(false)}
        onAnalyze={handleRefundAnalysis}
      />

      <RecommendationModal
        isOpen={showRecommendationModal}
        onClose={() => setShowRecommendationModal(false)}
        onComplete={handleRecommendationComplete}
        selectedCompanies={selectedInsuranceCompanies}
      />
    </div>
  )
}

// 현재 오류:
// Console Error

// Each child in a list should have a unique "key" prop.

// Check the render method of `div`. It was passed a child from ChatPage. See https://react.dev/link/warning-keys for more information.

// app/chat/[[...chat_id]]/page.tsx (576:17) @ ChatPage/<.children<.children<.children<.children<

//   574 |
//       <div className="max-w-3xl mx-auto space-y-4">
//   575 |
//       {messages.map((message, index) => (
// > 576 |
//       <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
//       |                 ^ 
//   577 |
//       <div
//   578 |
//       className={`flex space-x-3 max-w-2xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}
//   579 |
//       >

// Call Stack 23
// Show 20 ignore-listed frame(s)
// div
// unknown (0:0)
// ChatPage/<.children<.children<.children<.children<
// app/chat/[[...chat_id]]/page.tsx (576:17)
// ChatPage
// app/chat/[[...chat_id]]/page.tsx (575:25)


// TODO: /chat/{chat_id}에서 대화 시 새로운 대화로 간주하고 새 chat_id를 만드는게 아니라 form data의 body에 chat_id 포함하도록 해 기존 대화를 이어나가는 것으로 인식하도록
