"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FileText, TrendingUp, Shield, MessageCircle, Send, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'

interface NewChatModalProps {
  isOpen: boolean
  onClose: () => void
  onStartChat: (type: string, title?: string, initialMessage?: string) => void
}

export default function NewChatModal({ isOpen, onClose, onStartChat }: NewChatModalProps) {
  const [input, setInput] = useState("") // New state for the chat input
  const [showAllQuickQuestions, setShowAllQuickQuestions] = useState(false) // New state for showing all questions

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

  const displayedQuestions = showAllQuickQuestions ? quickStartQuestions : quickStartQuestions.slice(0, 4); // Changed from 6 to 4

  const handleFAQSelect = (question: string) => {
    onStartChat("general", question.length > 30 ? question.substring(0, 30) + "..." : question, question)
    onClose()
  }

  const handleFeatureClick = (featureTitle: string) => {
    let message = "";
    let chatType = "general"; // Default to general chat
    switch (featureTitle) {
      case '내 보험 약관 분석':
        message = "내 보험 약관 분석을 시작하고 싶어요.";
        chatType = "analysis"; // Can set a specific type if needed for initial message
        break;
      case '환급금 찾기':
        message = "환급금 찾기를 시작하고 싶어요.";
        chatType = "refund";
        break;
      case '보험 추천':
        message = "보험 추천을 시작하고 싶어요.";
        chatType = "comparison"; // Or 'recommendation' if a specific type exists
        break;
      default:
        message = `"${featureTitle}"에 대해 궁금합니다.`;
    }
    onStartChat(chatType, featureTitle, message);
    onClose();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim()) {
      onStartChat("general", input.length > 30 ? input.substring(0, 30) + "..." : input, input);
      setInput("");
      onClose();
    }
  };

  const handleClose = () => {
    onClose()
    setInput("")
    setShowAllQuickQuestions(false) // Reset state on close
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[80vh] flex flex-col p-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center space-x-2 text-xl">
            <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span>새로운 상담 시작하기</span>
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6">
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
                      key={index}
                      variant="outline"
                      className="text-left h-auto p-4 hover:bg-yellow-50 hover:border-yellow-300 bg-transparent justify-center text-sm"
                      onClick={() => handleFAQSelect(question)}
                    >
                      {question}
                    </Button>
                  ))}
                </div>
                {quickStartQuestions.length > 4 && ( // Changed from 6 to 4
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
        </div>

        {/* Input area at the bottom */}
        <div className="border-t bg-white p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            <div className="flex space-x-4">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="보험에 대해 궁금한 것을 물어보세요..."
                className="flex-1"
              />
              <Button
                type="submit"
                disabled={!input?.trim()}
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
      </DialogContent>
    </Dialog>
  )
}
