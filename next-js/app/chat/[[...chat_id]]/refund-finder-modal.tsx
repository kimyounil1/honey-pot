"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { UploadCloud, SearchCheck } from 'lucide-react'
import { Textarea } from "@/components/ui/textarea" // Textarea 임포트

interface RefundFinderModalProps {
  isOpen: boolean
  onClose: () => void
  onAnalyze: (textInput?: string) => void // textInput 추가
}

export default function RefundFinderModal({ isOpen, onClose, onAnalyze }: RefundFinderModalProps) {
  const [textInput, setTextInput] = useState("") // 텍스트 입력 상태 추가

  const handleAnalyze = () => {
    if (textInput.trim()) {
      onAnalyze(textInput)
      onClose()
      setTextInput("")
    }
  }

  const handleClose = () => {
    onClose()
    setTextInput("")
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">환급금 찾기</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* 메인 채팅 입력창 */}
          <div className="space-y-2">
            <Label htmlFor="refund-text-input">아래 예시처럼 입력 해주세요</Label>
            <Textarea // Textarea로 변경
              id="refund-text-input"
              placeholder="예시 : 한화생명 실손 2022형, 질병코드 S83.2 환급금은 얼마 받을 수 있을까?"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={6} // 높이 조절
            />
          </div>

          <div className="relative">
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">
                ⚠️ 직접 진단서 파일을 첨부하시는 경우, 채팅창에서 파일을 업로드 후 질문내용을 입력해주세요.
              </span>
            </div>
          </div>


          <div className="flex justify-end">
            <Button
              onClick={handleAnalyze}
              disabled={!textInput.trim()}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
            >
              <SearchCheck className="mr-2 h-4 w-4" />채팅 시작
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
