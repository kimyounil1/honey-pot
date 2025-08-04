"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FileText, TrendingUp, Shield, MessageCircle, Plus, Sparkles } from "lucide-react"

interface NewChatModalProps {
  isOpen: boolean
  onClose: () => void
  onStartChat: (type: string, title?: string) => void
}

export default function NewChatModal({ isOpen, onClose, onStartChat }: NewChatModalProps) {
  const [customTitle, setCustomTitle] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const chatCategories = [
    {
      id: "general",
      icon: MessageCircle,
      title: "일반 상담",
      description: "보험에 대한 기본적인 질문과 상담",
      color: "bg-blue-50 border-blue-200 hover:bg-blue-100",
      badge: "인기",
      badgeColor: "bg-blue-500",
    },
    {
      id: "refund",
      icon: TrendingUp,
      title: "환급금 찾기",
      description: "놓치고 있는 보험 환급금 및 혜택 분석",
      color: "bg-green-50 border-green-200 hover:bg-green-100",
      badge: "추천",
      badgeColor: "bg-green-500",
    },
    {
      id: "analysis",
      icon: FileText,
      title: "보험 약관 분석",
      description: "복잡한 보험 약관을 쉽게 분석하고 설명",
      color: "bg-purple-50 border-purple-200 hover:bg-purple-100",
      badge: "전문",
      badgeColor: "bg-purple-500",
    },
    {
      id: "comparison",
      icon: Shield,
      title: "보험 비교",
      description: "다른 보험 상품과의 비교 및 추천",
      color: "bg-orange-50 border-orange-200 hover:bg-orange-100",
      badge: "신규",
      badgeColor: "bg-orange-500",
    },
  ]

  const quickStartTemplates = [
    "내 보험 제대로 알고 싶어요",
    "놓친 환급금이 있는지 확인해주세요",
    "보험금 청구 방법을 알려주세요",
    "다른 보험사와 비교해주세요",
    "보험료를 줄일 수 있는 방법이 있나요?",
    "실손보험 중복 가입 확인해주세요",
  ]

  const handleStartChat = (categoryId: string) => {
    const category = chatCategories.find((c) => c.id === categoryId)
    const title = customTitle || `${category?.title} - ${new Date().toLocaleDateString()}`
    onStartChat(categoryId, title)
    onClose()
    setCustomTitle("")
    setSelectedCategory(null)
  }

  const handleQuickStart = (template: string) => {
    onStartChat("general", template)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2 text-xl">
            <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span>새로운 상담 시작하기</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* 채팅 제목 설정 */}
          <div className="space-y-2">
            <Label htmlFor="chat-title">채팅 제목 (선택사항)</Label>
            <Input
              id="chat-title"
              placeholder="예: 실손보험 환급금 문의"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
            />
          </div>

          {/* 상담 카테고리 선택 */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">상담 유형을 선택해주세요</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {chatCategories.map((category) => (
                <Card
                  key={category.id}
                  className={`cursor-pointer transition-all duration-200 ${category.color} ${
                    selectedCategory === category.id ? "ring-2 ring-yellow-400 shadow-lg" : ""
                  }`}
                  onClick={() => setSelectedCategory(category.id)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm">
                          <category.icon className="h-5 w-5 text-gray-600" />
                        </div>
                        <div>
                          <CardTitle className="text-base">{category.title}</CardTitle>
                        </div>
                      </div>
                      <Badge className={`${category.badgeColor} text-white text-xs`}>{category.badge}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-sm text-gray-600">{category.description}</p>
                    {selectedCategory === category.id && (
                      <Button
                        className="w-full mt-3 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                        onClick={() => handleStartChat(category.id)}
                      >
                        <Plus className="mr-2 h-4 w-4" />이 유형으로 시작하기
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* 빠른 시작 템플릿 */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">또는 빠른 질문으로 시작하기</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {quickStartTemplates.map((template, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="text-left h-auto p-4 hover:bg-yellow-50 hover:border-yellow-300 bg-transparent justify-start"
                  onClick={() => handleQuickStart(template)}
                >
                  <MessageCircle className="mr-3 h-4 w-4 text-gray-400" />
                  <span className="text-sm">{template}</span>
                </Button>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
