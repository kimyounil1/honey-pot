"use client"

import { useState } from "react"
import { useChat } from "@ai-sdk/react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  MessageCircle,
  Send,
  Plus,
  Search,
  History,
  FileText,
  TrendingUp,
  Shield,
  User,
  Menu,
  X,
  Trash2,
  MoreVertical,
} from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import Link from "next/link"
import NewChatModal from "./new-chat-modal"

interface ChatSession {
  id: string
  title: string
  type: string
  lastMessage: string
  timestamp: Date
  messageCount: number
}

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showNewChatModal, setShowNewChatModal] = useState(false)
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      id: "1",
      title: "실손보험 환급금 문의",
      type: "refund",
      lastMessage: "네, 확인해보니 약 150만원의 환급금이...",
      timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30분 전
      messageCount: 12,
    },
    {
      id: "2",
      title: "보험 약관 분석",
      type: "analysis",
      lastMessage: "해당 약관에 따르면 특약 조건이...",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2시간 전
      messageCount: 8,
    },
  ])

  const { messages, input, handleInputChange, handleSubmit, isLoading, setMessages } = useChat()

  const sidebarItems = [
    { icon: History, label: "채팅 기록", href: "/history" },
    { icon: FileText, label: "보험 진단", href: "/diagnosis" },
    { icon: TrendingUp, label: "환급금 분석", href: "/refund" },
    { icon: Shield, label: "나의 보험", href: "/my-insurance" },
  ]

  const quickStartQuestions = [
    "내 보험 제대로 알고 싶어요",
    "놓친 환급금이 있는지 확인해주세요",
    "보험금 청구 방법을 알려주세요",
    "다른 보험사와 비교해주세요",
  ]

  // 방식 1: 모달을 통한 새 채팅 시작
  const handleNewChat = () => {
    setShowNewChatModal(true)
  }

  const handleStartChatFromModal = (type: string, title?: string) => {
    const newChatId = Date.now().toString()
    setCurrentChatId(newChatId)
    setMessages([])

    const newSession: ChatSession = {
      id: newChatId,
      title: title || `새 상담 - ${new Date().toLocaleDateString()}`,
      type,
      lastMessage: "",
      timestamp: new Date(),
      messageCount: 0,
    }
    setChatSessions((prev) => [newSession, ...prev])
  }

  const handleDeleteChat = (chatId: string) => {
    setChatSessions((prev) => prev.filter((chat) => chat.id !== chatId))
    if (currentChatId === chatId) {
      setCurrentChatId(null)
      setMessages([])
    }
  }

  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId)
    // 실제로는 여기서 해당 채팅의 메시지를 로드해야 함
    setMessages([])
  }

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
        return "bg-purple-100 text-purple-700"
      case "comparison":
        return "bg-orange-100 text-orange-700"
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

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-50 w-80 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0`}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">꿀</span>
            </div>
            <span className="text-xl font-bold text-gray-800">꿀통</span>
          </div>
          <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {/* 새 채팅 버튼들 - 두 가지 방식 */}
          <div className="space-y-2">
            <Button
              className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
              onClick={handleNewChat}
            >
              <Plus className="mr-2 h-4 w-4" />새 채팅
            </Button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input placeholder="채팅 검색" className="pl-10" />
          </div>
        </div>

        {/* 채팅 기록 */}
        <div className="px-4">
          <h3 className="text-sm font-medium text-gray-500 mb-3">최근 채팅</h3>
          <ScrollArea className="h-64">
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
          </ScrollArea>
        </div>

        <nav className="px-4 mt-6 space-y-2">
          {sidebarItems.map((item, index) => (
            <Link key={index} href={item.href}>
              <Button variant="ghost" className="w-full justify-start">
                <item.icon className="mr-3 h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-4 left-4 right-4">
          <Separator className="mb-4" />
          <Link href="/login">
            <Button variant="outline" className="w-full bg-transparent">
              <User className="mr-2 h-4 w-4" />
              로그인
            </Button>
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-semibold text-gray-800">
              {currentChatId
                ? chatSessions.find((c) => c.id === currentChatId)?.title || "보험 상담 챗봇"
                : "보험 상담 챗봇"}
            </h1>
            <Badge variant="secondary">AI 상담사</Badge>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-green-600 border-green-600">
              온라인
            </Badge>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="max-w-3xl mx-auto">
              {/* Welcome Message */}
              <Card className="mb-8">
                <CardHeader className="text-center">
                  <div className="w-16 h-16 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="h-8 w-8 text-white" />
                  </div>
                  <CardTitle className="text-2xl">안녕하세요! 꿀통 AI 상담사입니다 🍯</CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                  <p className="text-gray-600 mb-6">
                    놓치고 있던 보험금과 환급 혜택을 찾아드릴게요.
                    <br />
                    궁금한 것이 있으시면 언제든 물어보세요!
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {quickStartQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        className="text-left h-auto p-4 hover:bg-yellow-50 hover:border-yellow-300 bg-transparent"
                        onClick={() => {
                          const event = { preventDefault: () => {} } as any
                          handleInputChange({ target: { value: question } } as any)
                          handleSubmit(event)
                        }}
                      >
                        {question}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Features */}
              <div className="grid md:grid-cols-3 gap-6">
                <Card className="text-center">
                  <CardContent className="pt-6">
                    <FileText className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">보험 약관 분석</h3>
                    <p className="text-sm text-gray-600">복잡한 보험 약관을 쉽게 설명해드려요</p>
                  </CardContent>
                </Card>
                <Card className="text-center">
                  <CardContent className="pt-6">
                    <TrendingUp className="h-12 w-12 text-green-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">환급금 찾기</h3>
                    <p className="text-sm text-gray-600">놓치고 있던 환급금을 찾아드려요</p>
                  </CardContent>
                </Card>
                <Card className="text-center">
                  <CardContent className="pt-6">
                    <Shield className="h-12 w-12 text-orange-500 mx-auto mb-4" />
                    <h3 className="font-semibold mb-2">보험 추천</h3>
                    <p className="text-sm text-gray-600">더 나은 보험 상품을 추천해드려요</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
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
                      {message.parts.map((part, i) => {
                        if (part.type === "text") {
                          return (
                            <div key={i} className="whitespace-pre-wrap">
                              {part.text}
                            </div>
                          )
                        }
                        return null
                      })}
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

        {/* Input Area */}
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

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* New Chat Modal */}
      <NewChatModal
        isOpen={showNewChatModal}
        onClose={() => setShowNewChatModal(false)}
        onStartChat={handleStartChatFromModal}
      />
    </div>
  )
}
