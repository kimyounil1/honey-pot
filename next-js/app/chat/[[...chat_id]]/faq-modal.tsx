"use client"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"

interface FAQModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectQuestion: (question: string) => void
}

const FAQ_QUESTIONS = [
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
]

export default function FAQModal({ isOpen, onClose, onSelectQuestion }: FAQModalProps) {
  const handleQuestionSelect = (question: string) => {
    onSelectQuestion(question)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl text-center">자주 하는 질문</DialogTitle>
        </DialogHeader>

        <div className="grid md:grid-cols-2 gap-3">
          {FAQ_QUESTIONS.map((question, index) => (
            <Button
              key={index}
              variant="outline"
              className="h-auto p-4 text-left justify-start hover:shadow-md transition-all duration-200"
              onClick={() => handleQuestionSelect(question)}
            >
              <span className="text-sm text-gray-700 leading-relaxed">{question}</span>
            </Button>
          ))}
        </div>

        <div className="text-center mt-4">
          <p className="text-sm text-gray-500">
            위 질문을 선택하시면 바로 채팅이 시작됩니다
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
